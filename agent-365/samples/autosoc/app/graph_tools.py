"""Bounded Microsoft Graph Security operations used by the triage graph."""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from os import environ
from typing import Any, TypeVar

import jwt
from azure.core.credentials import AccessToken
from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph import GraphServiceClient
from msgraph.generated.models.security.alert_classification import AlertClassification
from msgraph.generated.models.security.alert_comment import AlertComment
from msgraph.generated.models.security.alert_determination import AlertDetermination
from msgraph.generated.models.security.incident import Incident
from msgraph.generated.models.security.incident_status import IncidentStatus
from msgraph.generated.security.microsoft_graph_security_run_hunting_query.run_hunting_query_post_request_body import (
    RunHuntingQueryPostRequestBody,
)

from token_manager import get_token


logger = logging.getLogger(__name__)
ResultT = TypeVar("ResultT")
INCIDENT_COMMENT_MAX_LENGTH = 1_000


class GraphSecurityError(Exception):
    """Raised when a bounded Graph operation cannot be completed."""


@dataclass
class AlertsQueryParameters:
    """OData parameters needed when listing incident alerts."""

    filter: str | None = None
    top: int | None = None

    def get_query_parameter(self, original_name: str) -> str:
        return {"filter": "%24filter", "top": "%24top"}.get(
            original_name, original_name
        )


class RawAccessTokenProvider:
    """Expose an exchanged agent-user token through the Azure credential contract."""

    def __init__(self, token: str) -> None:
        self._token = token

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        payload = jwt.decode(
            self._token,
            options={"verify_signature": False},
        )
        return AccessToken(self._token, expires_on=int(payload["exp"]))


class GraphSecurityClient:
    """Narrow Graph client owned by the AutoSOC process."""

    def __init__(
        self,
        *,
        request_timeout_seconds: float | None = None,
        max_attempts: int | None = None,
        graph_client: GraphServiceClient | None = None,
    ) -> None:
        self._client = graph_client
        self._injected_client = graph_client is not None
        self._client_token: str | None = None
        self._tenant_id = environ.get(
            "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID"
        )
        self._agent_id = environ.get("AGENTIC_INSTANCE_ID")
        self._agent_user = environ.get("AGENTIC_USER_ID")
        self._request_timeout_seconds = request_timeout_seconds or float(
            environ.get("GRAPH_REQUEST_TIMEOUT_SECONDS", "60")
        )
        self._max_attempts = max_attempts or int(environ.get("GRAPH_MAX_ATTEMPTS", "4"))

    async def get_incident(self, incident_id: str) -> dict[str, Any]:
        """Fetch one incident and return a JSON-compatible bounded representation."""
        client = await self._get_client()
        response = await self._execute(
            "get_incident",
            lambda: client.security.incidents.by_incident_id(incident_id).get(),
        )
        if response is None:
            raise GraphSecurityError(f"Incident {incident_id} was not found")
        return _json_value(response)

    async def list_incident_alerts(
        self,
        incident_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch alerts associated with an incident, bounded before graph state."""
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        query_params = AlertsQueryParameters(
            filter=f"incidentId eq '{_odata_literal(incident_id)}'",
            top=limit,
        )
        client = await self._get_client()
        response = await self._execute(
            "list_incident_alerts",
            lambda: client.security.alerts_v2.get(
                request_configuration=RequestConfiguration(query_parameters=query_params)
            ),
        )
        return [_json_value(alert) for alert in (response.value or [])[:limit]]

    async def run_hunting_query(
        self,
        query: str,
        timespan: str,
        *,
        result_limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Run one catalog query and bound rows returned to a hunt worker."""
        if not query.strip() or len(query) > 50_000:
            raise ValueError("query must contain between 1 and 50000 characters")
        if not 1 <= result_limit <= 200:
            raise ValueError("result_limit must be between 1 and 200")
        client = await self._get_client()
        request_body = RunHuntingQueryPostRequestBody(query=query, timespan=timespan)
        response = await self._execute(
            "run_hunting_query",
            lambda: client.security.microsoft_graph_security_run_hunting_query.post(
                request_body
            ),
        )
        rows = response.results or []
        return [_json_value(row) for row in rows[:result_limit]]

    async def add_incident_comment(self, incident_id: str, comment: str) -> None:
        """Add one bounded triage report to an incident."""
        comment = comment.strip()
        if not comment:
            raise ValueError("comment is required")
        client = await self._get_client()
        request_body = AlertComment(
            odata_type=None,
            comment=comment[:INCIDENT_COMMENT_MAX_LENGTH],
        )
        url = f"https://graph.microsoft.com/v1.0/security/incidents/{incident_id}/comments"
        await self._execute(
            "add_incident_comment",
            lambda: client.security.incidents.with_url(url).post(request_body),
        )

    async def update_incident(
        self,
        incident_id: str,
        *,
        status: str,
        classification: str,
        determination: str,
        assigned_to: str | None,
        resolving_comment: str | None = None,
    ) -> None:
        """Apply a validated assessment decision to an incident."""
        body = Incident(
            status=_parse_enum(IncidentStatus, status),
            classification=_parse_enum(AlertClassification, classification),
            determination=_parse_enum(AlertDetermination, determination),
            assigned_to=assigned_to,
            resolving_comment=resolving_comment[:4_000] if resolving_comment else None,
        )
        client = await self._get_client()
        await self._execute(
            "update_incident",
            lambda: client.security.incidents.by_incident_id(incident_id).patch(body),
        )

    async def close(self) -> None:
        """Release resources owned by this wrapper."""

    async def _get_client(self) -> GraphServiceClient:
        if self._injected_client:
            return self._client
        token = await get_token(
            tenant_id=self._tenant_id,
            agent_id=self._agent_id,
            agent_user=self._agent_user,
            scopes=["https://graph.microsoft.com/.default"],
        )
        if self._client is None or token != self._client_token:
            self._client = GraphServiceClient(credentials=RawAccessTokenProvider(token))
            self._client_token = token
        return self._client

    async def _execute(
        self,
        operation_name: str,
        operation: Callable[[], Awaitable[ResultT]],
    ) -> ResultT:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                return await asyncio.wait_for(
                    operation(),
                    timeout=self._request_timeout_seconds,
                )
            except APIError as exc:
                last_error = exc
                if not _is_transient(exc) or attempt == self._max_attempts:
                    break
                delay = _retry_delay(exc, attempt)
            except TimeoutError as exc:
                last_error = exc
                if attempt == self._max_attempts:
                    break
                delay = min(2 ** (attempt - 1), 8) + random.random()

            logger.warning(
                "Transient Graph failure operation=%s attempt=%d/%d retry_seconds=%.2f",
                operation_name,
                attempt,
                self._max_attempts,
                delay,
            )
            await asyncio.sleep(delay)

        raise GraphSecurityError(f"Graph operation {operation_name} failed") from last_error


def _is_transient(error: APIError) -> bool:
    status = error.response_status_code
    return status == 429 or (status is not None and 500 <= status < 600)


def _retry_delay(error: APIError, attempt: int) -> float:
    headers = error.response_headers or {}
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return min(2 ** (attempt - 1), 8) + random.random()


def _odata_literal(value: str) -> str:
    return value.replace("'", "''")


def _parse_enum(enum_type: type[Enum], value: str) -> Enum:
    normalized = value.strip().lower()
    for member in enum_type:
        if member.name.lower() == normalized or str(member.value).lower() == normalized:
            return member
    choices = ", ".join(str(member.value) for member in enum_type)
    raise ValueError(f"Invalid {enum_type.__name__} '{value}'. Expected one of: {choices}")


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]

    backing_store = getattr(value, "backing_store", None)
    if backing_store and hasattr(backing_store, "enumerate_"):
        return {
            key: _json_value(item)
            for key, item in backing_store.enumerate_()
            if item is not None and key != "additional_data"
        }
    data = getattr(value, "additional_data", None)
    if data:
        return _json_value(data)
    return str(value)


