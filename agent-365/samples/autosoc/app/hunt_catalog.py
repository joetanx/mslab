"""Validated KQL hunt catalog used by the AutoSOC orchestrator."""

import json
from dataclasses import dataclass
from typing import Callable

from models import EntityType, IncidentContext


MAX_ENTITY_VALUES = 50
MAX_ENTITY_LENGTH = 512


@dataclass(frozen=True)
class HuntDefinition:
    """Static metadata and renderer for one bounded hunt capability."""

    hunt_id: str
    name: str
    description: str
    required_entity_groups: tuple[frozenset[EntityType], ...]
    timespan: str
    projected_columns: tuple[str, ...]
    renderer: Callable[[IncidentContext], str]

    def is_eligible(self, context: IncidentContext) -> bool:
        """Return whether every required group has at least one available entity type."""
        return all(
            any(context.entities.get(entity_type) for entity_type in group)
            for group in self.required_entity_groups
        )

    def render(self, context: IncidentContext) -> str:
        """Render a query only after deterministic eligibility validation."""
        if not self.is_eligible(context):
            raise ValueError(f"Hunt {self.hunt_id} is not eligible for this incident")
        return self.renderer(context)


def _values(context: IncidentContext, *entity_types: EntityType) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for entity_type in entity_types:
        for raw_value in context.entities.get(entity_type, []):
            value = raw_value.strip()[:MAX_ENTITY_LENGTH]
            comparison_value = value.casefold()
            if value and comparison_value not in seen:
                seen.add(comparison_value)
                values.append(value)
            if len(values) >= MAX_ENTITY_VALUES:
                return values
    return values


def _dynamic(values: list[str]) -> str:
    """Encode values as JSON inside a KQL dynamic literal, not query syntax."""
    return f"dynamic({json.dumps(values, ensure_ascii=True)})"


def _all_entities(context: IncidentContext) -> list[str]:
    return _values(context, *tuple(EntityType))


def _related_alerts(context: IncidentContext) -> str:
    return f"""let incident_entities = {_dynamic(_all_entities(context))};
SecurityAlert
| where tostring(parse_json(ExtendedProperties).IncidentId) != {json.dumps(context.incident_id)}
| where tostring(Entities) has_any (incident_entities)
| summarize AlertCount=count(), LastSeen=max(TimeGenerated)
    by AlertName, ProviderName, ProductName, Status, CompromisedEntity
| project AlertName, ProviderName, ProductName, Status, CompromisedEntity, AlertCount, LastSeen
| top 100 by LastSeen desc"""


def _threat_intelligence(context: IncidentContext) -> str:
    values = _values(
        context,
        EntityType.IP_ADDRESS,
        EntityType.DOMAIN,
        EntityType.URL,
        EntityType.FILE_HASH,
    )
    return f"""let observables = {_dynamic(values)};
ThreatIntelIndicators
| where set_has_element(observables, ObservableValue)
| summarize arg_max(Modified, *) by ObservableValue
| project Modified, ObservableKey, ObservableValue, IsActive, Confidence
| top 100 by Modified desc"""


def _windows_sign_in(context: IncidentContext) -> str:
    hosts = _dynamic(_values(context, EntityType.HOSTNAME))
    users = _dynamic(_values(context, EntityType.USER, EntityType.UPN))
    return f"""let incident_hosts = {hosts};
let incident_users = {users};
SecurityEvent
| where EventID == 4625
| where Computer has_any (incident_hosts) or Account has_any (incident_users)
| summarize FailureCount=count(), LastSeen=max(TimeGenerated)
    by Computer, Account, Activity, IpAddress
| project Computer, Account, Activity, IpAddress, FailureCount, LastSeen
| top 100 by FailureCount desc"""


def _linux_sign_in(context: IncidentContext) -> str:
    hosts = _dynamic(_values(context, EntityType.HOSTNAME))
    users = _dynamic(_values(context, EntityType.USER, EntityType.UPN))
    return f"""let incident_hosts = {hosts};
let incident_users = {users};
Syslog
| where Facility in ("auth", "authpriv") and ProcessName =~ "sshd"
| where SyslogMessage contains "failed password"
| where HostName has_any (incident_hosts) or SyslogMessage has_any (incident_users)
| summarize FailureCount=count(), LastSeen=max(TimeGenerated),
    SampleMessages=make_set(SyslogMessage, 5) by HostName
| project HostName, FailureCount, LastSeen, SampleMessages
| top 100 by FailureCount desc"""


def _entra_sign_in(context: IncidentContext) -> str:
    users = _dynamic(_values(context, EntityType.USER, EntityType.UPN))
    return f"""let incident_users = {users};
SigninLogs
| where ResultType != "0"
| where Identity has_any (incident_users) or UserPrincipalName has_any (incident_users)
| summarize FailureCount=count(), LastSeen=max(TimeGenerated),
    ResultDescriptions=make_set(ResultDescription, 5), IPAddresses=make_set(IPAddress, 10)
    by Identity, UserPrincipalName
| project Identity, UserPrincipalName, FailureCount, LastSeen, ResultDescriptions, IPAddresses
| top 100 by FailureCount desc"""


ANY_ENTITY = (frozenset(EntityType),)
HOST_OR_USER = (
    frozenset(
        {
            EntityType.HOSTNAME,
            EntityType.USER,
            EntityType.UPN,
        }
    ),
)
USER_ENTITY = (frozenset({EntityType.USER, EntityType.UPN}),)
OBSERVABLE_ENTITY = (
    frozenset(
        {
            EntityType.IP_ADDRESS,
            EntityType.DOMAIN,
            EntityType.URL,
            EntityType.FILE_HASH,
        }
    ),
)


HUNT_CATALOG: dict[str, HuntDefinition] = {
    definition.hunt_id: definition
    for definition in (
        HuntDefinition(
            hunt_id="related_alerts",
            name="Related alerts",
            description="Find other alerts that contain entities from this incident.",
            required_entity_groups=ANY_ENTITY,
            timespan="P30D",
            projected_columns=(
                "AlertName",
                "ProviderName",
                "ProductName",
                "Status",
                "CompromisedEntity",
                "AlertCount",
                "LastSeen",
            ),
            renderer=_related_alerts,
        ),
        HuntDefinition(
            hunt_id="threat_intelligence",
            name="Threat intelligence",
            description="Match incident observables with current threat intelligence.",
            required_entity_groups=OBSERVABLE_ENTITY,
            timespan="P30D",
            projected_columns=(
                "Modified",
                "ObservableKey",
                "ObservableValue",
                "IsActive",
                "Confidence",
            ),
            renderer=_threat_intelligence,
        ),
        HuntDefinition(
            hunt_id="windows_sign_in",
            name="Windows sign-in failures",
            description="Find failed Windows sign-ins related to incident hosts or users.",
            required_entity_groups=HOST_OR_USER,
            timespan="P7D",
            projected_columns=(
                "Computer",
                "Account",
                "Activity",
                "IpAddress",
                "FailureCount",
                "LastSeen",
            ),
            renderer=_windows_sign_in,
        ),
        HuntDefinition(
            hunt_id="linux_sign_in",
            name="Linux SSH sign-in failures",
            description="Find failed SSH sign-ins related to incident hosts or users.",
            required_entity_groups=HOST_OR_USER,
            timespan="P7D",
            projected_columns=("HostName", "FailureCount", "LastSeen", "SampleMessages"),
            renderer=_linux_sign_in,
        ),
        HuntDefinition(
            hunt_id="entra_sign_in",
            name="Entra sign-in failures",
            description="Find failed Entra sign-ins involving incident users.",
            required_entity_groups=USER_ENTITY,
            timespan="P7D",
            projected_columns=(
                "Identity",
                "UserPrincipalName",
                "FailureCount",
                "LastSeen",
                "ResultDescriptions",
                "IPAddresses",
            ),
            renderer=_entra_sign_in,
        ),
    )
}


def eligible_hunts(context: IncidentContext) -> list[HuntDefinition]:
    """Return catalog hunts whose entity requirements are satisfied."""
    return [definition for definition in HUNT_CATALOG.values() if definition.is_eligible(context)]