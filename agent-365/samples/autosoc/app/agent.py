"""Explicit LangGraph workflow for autonomous Defender incident triage."""

import asyncio
import json
import logging
import operator
from os import environ
from typing import Annotated, Any, NotRequired, TypedDict

from azure.identity import ManagedIdentityCredential
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from graph_tools import GraphSecurityClient, INCIDENT_COMMENT_MAX_LENGTH
from hunt_catalog import HUNT_CATALOG, HuntDefinition, eligible_hunts
from models import (
    Assessment,
    AssessmentCategory,
    AssessmentProposal,
    ContextExtraction,
    EntityType,
    HuntPlan,
    HuntResult,
    HuntSelection,
    HuntStatus,
    IncidentContext,
)


logger = logging.getLogger(__name__)


class TriageState(TypedDict):
    incident_id: str
    correlation_id: str
    context: NotRequired[IncidentContext]
    selected_hunts: NotRequired[list[HuntPlan]]
    hunt_results: Annotated[list[HuntResult], operator.add]
    assessment: NotRequired[Assessment]


class HuntWorkerState(TypedDict):
    context: IncidentContext
    hunt_plan: HuntPlan


class AutoSOCAgent:
    """Compile and run the bounded incident triage graph."""

    def __init__(
        self,
        *,
        model: BaseChatModel | None = None,
        graph_client: GraphSecurityClient | None = None,
    ) -> None:
        self._model_credential: ManagedIdentityCredential | None = None
        if model is None:
            self._model_credential = ManagedIdentityCredential(
                client_id=environ.get("UAMI_CLIENT_ID")
            )
            model = init_chat_model(
                f"azure_ai:{environ['FOUNDRY_MODEL']}",
                project_endpoint=environ["FOUNDRY_PROJECT_ENDPOINT"],
                credential=self._model_credential,
            )
        self._model = model
        self._context_model = model.with_structured_output(ContextExtraction)
        self._selection_model = model.with_structured_output(HuntSelection)
        self._assessment_model = model.with_structured_output(AssessmentProposal)
        self._graph_client = graph_client or GraphSecurityClient()
        self._checkpointer = InMemorySaver()
        self._graph = self._build_graph()
        self._max_hunts = int(environ.get("MAX_HUNTS_PER_INCIDENT", "5"))
        self._overall_timeout = float(environ.get("TRIAGE_TIMEOUT_SECONDS", "300"))

    def _build_graph(self):
        builder = StateGraph(TriageState)
        builder.add_node("load_context", self._load_context)
        builder.add_node("plan_hunts", self._plan_hunts)
        builder.add_node("run_hunt", self._run_hunt)
        builder.add_node("assess", self._assess)
        builder.add_node("write_back", self._write_back)
        builder.add_edge(START, "load_context")
        builder.add_edge("load_context", "plan_hunts")
        builder.add_conditional_edges("plan_hunts", self._fan_out_hunts)
        builder.add_edge("run_hunt", "assess")
        builder.add_edge("assess", "write_back")
        builder.add_edge("write_back", END)
        return builder.compile(checkpointer=self._checkpointer)

    async def run_triage(self, incident_id: str, correlation_id: str) -> None:
        """Run one graph and always remove its process-local checkpoint."""
        config = {
            "configurable": {"thread_id": correlation_id},
            "recursion_limit": 12,
        }
        try:
            await asyncio.wait_for(
                self._graph.ainvoke(
                    {
                        "incident_id": incident_id,
                        "correlation_id": correlation_id,
                        "hunt_results": [],
                    },
                    config=config,
                ),
                timeout=self._overall_timeout,
            )
        except Exception as exc:
            logger.exception(
                "Triage graph failed incident_id=%s correlation_id=%s",
                incident_id,
                correlation_id,
            )
            try:
                await self._graph_client.add_incident_comment(
                    incident_id,
                    "AutoSOC triage failed before completion. Review Container Apps logs "
                    f"with correlation ID {correlation_id}.",
                )
            except Exception:
                logger.exception(
                    "Unable to write failure comment incident_id=%s correlation_id=%s",
                    incident_id,
                    correlation_id,
                )
            raise
        finally:
            await self._checkpointer.adelete_thread(correlation_id)

    async def _load_context(self, state: TriageState) -> dict[str, Any]:
        incident, alerts = await asyncio.gather(
            self._graph_client.get_incident(state["incident_id"]),
            self._graph_client.list_incident_alerts(state["incident_id"]),
        )
        source = _bounded_json({"incident": incident, "alerts": alerts})
        extraction = await self._context_model.ainvoke(
            "Extract only security-relevant entities explicitly present in this Defender "
            "incident and its alerts. Do not infer or invent values. Produce a concise "
            f"overview. Source JSON:\n{source}"
        )
        context = IncidentContext(
            incident_id=state["incident_id"],
            display_name=str(incident.get("display_name") or incident.get("displayName") or "")[:512],
            severity=_optional_text(incident.get("severity"), 64),
            overview=extraction.overview,
            entities={
                entity_type: _normalize_entities(
                    getattr(extraction.entities, entity_type.value)
                )
                for entity_type in EntityType
            },
        )
        logger.info(
            "Incident context loaded incident_id=%s correlation_id=%s alerts=%d entities=%d",
            state["incident_id"],
            state["correlation_id"],
            len(alerts),
            sum(len(values) for values in context.entities.values()),
        )
        return {"context": context}

    async def _plan_hunts(self, state: TriageState) -> dict[str, Any]:
        context = state["context"]
        candidates = eligible_hunts(context)
        if not candidates:
            return {"selected_hunts": []}
        catalog = [
            {
                "hunt_id": definition.hunt_id,
                "name": definition.name,
                "description": definition.description,
            }
            for definition in candidates
        ]
        selection = await self._selection_model.ainvoke(
            "Select only hunts that can materially clarify this incident. Do not select a "
            "hunt merely because it is available. Return catalog hunt IDs exactly.\n"
            f"Incident context: {context.model_dump_json()}\n"
            f"Eligible catalog: {json.dumps(catalog)}"
        )
        eligible_ids = {definition.hunt_id for definition in candidates}
        selected: list[HuntPlan] = []
        seen: set[str] = set()
        for plan in selection.hunts:
            if plan.hunt_id in eligible_ids and plan.hunt_id not in seen:
                seen.add(plan.hunt_id)
                selected.append(plan)
            if len(selected) >= self._max_hunts:
                break
        logger.info(
            "Hunts planned incident_id=%s correlation_id=%s hunts=%s",
            state["incident_id"],
            state["correlation_id"],
            [plan.hunt_id for plan in selected],
        )
        return {"selected_hunts": selected}

    def _fan_out_hunts(self, state: TriageState) -> str | list[Send]:
        selected = state.get("selected_hunts", [])
        if not selected:
            return "assess"
        return [
            Send("run_hunt", {"context": state["context"], "hunt_plan": plan})
            for plan in selected
        ]

    async def _run_hunt(self, state: HuntWorkerState) -> dict[str, list[HuntResult]]:
        plan = state["hunt_plan"]
        definition = HUNT_CATALOG[plan.hunt_id]
        try:
            rows = await self._graph_client.run_hunting_query(
                definition.render(state["context"]),
                definition.timespan,
                result_limit=100,
            )
            result = HuntResult(
                hunt_id=plan.hunt_id,
                status=HuntStatus.SUCCEEDED,
                result_count=len(rows),
                summary=(
                    f"{definition.name} returned {len(rows)} projected result rows. "
                    f"Selection rationale: {plan.rationale}"
                ),
                projected_columns=list(definition.projected_columns),
                evidence=rows[:5],
            )
        except Exception as exc:
            logger.exception("Hunt failed hunt_id=%s", plan.hunt_id)
            result = HuntResult(
                hunt_id=plan.hunt_id,
                status=HuntStatus.FAILED,
                summary=f"{definition.name} did not complete.",
                projected_columns=list(definition.projected_columns),
                error=str(exc)[:1_000],
            )
        return {"hunt_results": [result]}

    async def _assess(self, state: TriageState) -> dict[str, Assessment]:
        context = state["context"]
        results = state.get("hunt_results", [])
        proposal = await self._assessment_model.ainvoke(
            "Assess this Defender incident as false_positive, benign_true_positive, "
            "true_positive, or suspicious. Use only supplied evidence. Failed hunts mean "
            "coverage is incomplete. Select the most specific supported determination; "
            "the application will derive Defender status and classification.\n"
            f"Context: {context.model_dump_json()}\n"
            f"Hunt results: {json.dumps([result.model_dump(mode='json') for result in results])}"
        )
        assessment = Assessment.from_proposal(proposal)
        if any(result.status == HuntStatus.FAILED for result in results) and assessment.status == "resolved":
            assessment = Assessment(
                category=AssessmentCategory.SUSPICIOUS,
                confidence=min(assessment.confidence, 0.5),
                rationale=(
                    "Hunting coverage was incomplete, so AutoSOC did not resolve the incident. "
                    + assessment.rationale
                )[:4_000],
                classification="unknown",
                determination="notEnoughDataToValidate",
                status="inProgress",
            )
        return {"assessment": assessment}

    async def _write_back(self, state: TriageState) -> dict[str, Any]:
        assessment = state["assessment"]
        comment = _format_comment(
            state["correlation_id"],
            assessment,
            state.get("hunt_results", []),
        )
        await self._graph_client.add_incident_comment(state["incident_id"], comment)
        resolved = assessment.status == "resolved"
        await self._graph_client.update_incident(
            state["incident_id"],
            status=assessment.status,
            classification=assessment.classification,
            determination=assessment.determination,
            assigned_to=environ.get(
                "ASSIGNEE_RESOLVED" if resolved else "ASSIGNEE_IN_PROGRESS"
            ),
            resolving_comment=assessment.rationale if resolved else None,
        )
        return {}

    async def close(self) -> None:
        """Close credentials and Graph transports owned by the runner."""
        await self._graph_client.close()
        if self._model_credential is not None:
            self._model_credential.close()


def _normalize_entities(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values[:50]:
        value = str(raw_value).strip()[:512]
        comparison_value = value.casefold()
        if value and comparison_value not in seen:
            seen.add(comparison_value)
            normalized.append(value)
    return normalized


def _optional_text(value: Any, limit: int) -> str | None:
    return str(value)[:limit] if value is not None else None


def _bounded_json(value: Any, limit: int = 30_000) -> str:
    return json.dumps(value, ensure_ascii=True, default=str)[:limit]


def _format_comment(
    correlation_id: str,
    assessment: Assessment,
    results: list[HuntResult],
) -> str:
    lines = [
        "AutoSOC triage",
        f"Correlation ID: {correlation_id}",
        f"Assessment: {assessment.category.value} ({assessment.confidence:.0%} confidence)",
        f"Rationale: {assessment.rationale}",
        "Hunts:",
    ]
    if not results:
        lines.append("- No catalog hunt was selected or eligible.")
    for result in results:
        detail = result.summary if result.status == HuntStatus.SUCCEEDED else result.error
        lines.append(
            f"- {result.hunt_id}: {result.status.value}; {result.result_count} rows; {detail or 'no detail'}"
        )
    return "\n".join(lines)[:INCIDENT_COMMENT_MAX_LENGTH]
