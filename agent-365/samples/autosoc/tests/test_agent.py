from agent import AutoSOCAgent
from models import (
    Assessment,
    AssessmentCategory,
    AssessmentProposal,
    ContextExtraction,
    EntityCollection,
    HuntPlan,
    HuntSelection,
)


class StructuredModel:
    def __init__(self, schema):
        self.schema = schema

    async def ainvoke(self, _prompt):
        if self.schema is ContextExtraction:
            return ContextExtraction(
                overview="Suspicious sign-in incident.",
                entities=EntityCollection(
                    ip_addresses=["192.0.2.1"],
                    hostnames=["host-1"],
                    upns=["user@example.com"],
                ),
            )
        if self.schema is HuntSelection:
            return HuntSelection(
                hunts=[
                    HuntPlan(hunt_id="threat_intelligence", rationale="IP observable"),
                    HuntPlan(hunt_id="entra_sign_in", rationale="User sign-in"),
                ]
            )
        return AssessmentProposal(
            category=AssessmentCategory.SUSPICIOUS,
            confidence=0.7,
            rationale="Evidence requires analyst review.",
            determination="malware",
        )


class FakeModel:
    def with_structured_output(self, schema):
        return StructuredModel(schema)


class FakeGraphClient:
    def __init__(self):
        self.queries = []
        self.comments = []
        self.updates = []

    async def get_incident(self, incident_id):
        return {"id": incident_id, "displayName": "Test", "severity": "medium"}

    async def list_incident_alerts(self, _incident_id):
        return [{"title": "Test alert"}]

    async def run_hunting_query(self, query, timespan, *, result_limit):
        self.queries.append((query, timespan, result_limit))
        return [{"value": "evidence"}]

    async def add_incident_comment(self, incident_id, comment):
        self.comments.append((incident_id, comment))

    async def update_incident(self, incident_id, **updates):
        self.updates.append((incident_id, updates))

    async def close(self):
        pass


async def test_graph_fans_out_compacts_and_writes_back(monkeypatch):
    monkeypatch.setenv("ASSIGNEE_IN_PROGRESS", "soc@example.com")
    graph_client = FakeGraphClient()
    agent = AutoSOCAgent(model=FakeModel(), graph_client=graph_client)

    await agent.run_triage("incident-1", "correlation-1")

    assert len(graph_client.queries) == 2
    assert all(result_limit == 100 for _, _, result_limit in graph_client.queries)
    assert len(graph_client.comments) == 1
    assert "threat_intelligence" in graph_client.comments[0][1]
    assert "entra_sign_in" in graph_client.comments[0][1]
    assert graph_client.updates == [
        (
            "incident-1",
            {
                "status": "inProgress",
                "classification": "unknown",
                "determination": "unknown",
                "assigned_to": "soc@example.com",
                "resolving_comment": None,
            },
        )
    ]
    assert "correlation-1" not in agent._checkpointer.storage
