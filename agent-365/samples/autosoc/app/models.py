"""Typed contracts shared by the AutoSOC HTTP service and triage graph."""

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


IncidentId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class TriageRequest(BaseModel):
    """Request accepted from the Sentinel Logic App playbook."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    incident_id: IncidentId = Field(alias="incidentId")


class TriageAccepted(BaseModel):
    """Immediate acknowledgement returned for accepted background work."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = "accepted"
    incident_id: IncidentId = Field(alias="incidentId")
    correlation_id: str = Field(alias="correlationId")


class EntityType(str, Enum):
    IP_ADDRESS = "ip_addresses"
    DOMAIN = "domains"
    URL = "urls"
    FILE_HASH = "file_hashes"
    HOSTNAME = "hostnames"
    USER = "users"
    UPN = "upns"


class EntityCollection(BaseModel):
    """Entity taxonomy produced by structured incident extraction."""

    ip_addresses: list[str] = Field(default_factory=list, max_length=50)
    domains: list[str] = Field(default_factory=list, max_length=50)
    urls: list[str] = Field(default_factory=list, max_length=50)
    file_hashes: list[str] = Field(default_factory=list, max_length=50)
    hostnames: list[str] = Field(default_factory=list, max_length=50)
    users: list[str] = Field(default_factory=list, max_length=50)
    upns: list[str] = Field(default_factory=list, max_length=50)


class ContextExtraction(BaseModel):
    """Model-generated compact interpretation of incident and alert fields."""

    overview: str = Field(max_length=4_000)
    entities: EntityCollection


class IncidentContext(BaseModel):
    """Bounded incident details retained in graph state."""

    incident_id: IncidentId
    display_name: str = Field(default="", max_length=512)
    severity: str | None = Field(default=None, max_length=64)
    overview: str = Field(default="", max_length=4_000)
    entities: dict[EntityType, list[str]] = Field(default_factory=dict)


class HuntStatus(str, Enum):
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


class HuntPlan(BaseModel):
    """A catalog hunt selected for one incident."""

    hunt_id: str = Field(min_length=1, max_length=64)
    rationale: str = Field(default="", max_length=1_000)


class HuntSelection(BaseModel):
    """Structured orchestrator output constrained to catalog identifiers later."""

    hunts: list[HuntPlan] = Field(default_factory=list, max_length=10)


class HuntResult(BaseModel):
    """Compact evidence returned by an isolated hunt worker."""

    hunt_id: str
    status: HuntStatus
    result_count: int = Field(default=0, ge=0)
    summary: str = Field(default="", max_length=2_000)
    projected_columns: list[str] = Field(default_factory=list, max_length=20)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=10)
    error: str | None = Field(default=None, max_length=1_000)


class AssessmentCategory(str, Enum):
    FALSE_POSITIVE = "false_positive"
    BENIGN_TRUE_POSITIVE = "benign_true_positive"
    TRUE_POSITIVE = "true_positive"
    SUSPICIOUS = "suspicious"


AssessmentDetermination = Literal[
    "unknown",
    "apt",
    "malware",
    "securityPersonnel",
    "securityTesting",
    "unwantedSoftware",
    "other",
    "multiStagedAttack",
    "compromisedAccount",
    "phishing",
    "maliciousUserActivity",
    "notMalicious",
    "notEnoughDataToValidate",
    "confirmedActivity",
    "lineOfBusinessApplication",
]


class AssessmentProposal(BaseModel):
    """Model-generated reasoning before deterministic Defender field mapping."""

    category: AssessmentCategory
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=4_000)
    determination: AssessmentDetermination = Field(
        default="unknown",
        description="Most specific determination supported by the supplied evidence.",
    )


class Assessment(BaseModel):
    """Validated decision used by the deterministic write-back node."""

    category: AssessmentCategory
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=4_000)
    classification: Literal[
        "unknown",
        "falsePositive",
        "truePositive",
        "informationalExpectedActivity",
    ]
    determination: AssessmentDetermination
    status: Literal["active", "inProgress", "resolved", "redirected"]

    @classmethod
    def from_proposal(cls, proposal: AssessmentProposal) -> "Assessment":
        """Map model reasoning to a safe, internally consistent Defender update."""
        resolved_determinations = {
            "notMalicious",
            "notEnoughDataToValidate",
            "securityTesting",
            "confirmedActivity",
            "lineOfBusinessApplication",
        }
        malicious_determinations = {
            "apt",
            "malware",
            "unwantedSoftware",
            "other",
            "multiStagedAttack",
            "compromisedAccount",
            "phishing",
            "maliciousUserActivity",
        }
        if proposal.category == AssessmentCategory.FALSE_POSITIVE:
            classification = "falsePositive"
            status = "resolved"
            determination = (
                proposal.determination
                if proposal.determination in resolved_determinations
                else "notEnoughDataToValidate"
            )
        elif proposal.category == AssessmentCategory.BENIGN_TRUE_POSITIVE:
            classification = "informationalExpectedActivity"
            status = "resolved"
            determination = (
                proposal.determination
                if proposal.determination in resolved_determinations
                else "confirmedActivity"
            )
        elif proposal.category == AssessmentCategory.TRUE_POSITIVE:
            classification = "truePositive"
            status = "inProgress"
            determination = (
                proposal.determination
                if proposal.determination in malicious_determinations
                else "other"
            )
        else:
            classification = "unknown"
            status = "inProgress"
            determination = (
                proposal.determination
                if proposal.determination in {"unknown", "notEnoughDataToValidate"}
                else "unknown"
            )
        return cls(
            category=proposal.category,
            confidence=proposal.confidence,
            rationale=proposal.rationale,
            classification=classification,
            determination=determination,
            status=status,
        )

    @model_validator(mode="after")
    def validate_decision_matrix(self) -> "Assessment":
        """Reject category combinations that could mutate Defender incorrectly."""
        resolved_determinations = {
            "notMalicious",
            "notEnoughDataToValidate",
            "securityTesting",
            "confirmedActivity",
            "lineOfBusinessApplication",
        }
        malicious_determinations = {
            "apt",
            "malware",
            "unwantedSoftware",
            "other",
            "multiStagedAttack",
            "compromisedAccount",
            "phishing",
            "maliciousUserActivity",
        }
        if self.category == AssessmentCategory.FALSE_POSITIVE:
            valid = (
                self.status == "resolved"
                and self.classification == "falsePositive"
                and self.determination in resolved_determinations
            )
        elif self.category == AssessmentCategory.BENIGN_TRUE_POSITIVE:
            valid = (
                self.status == "resolved"
                and self.classification == "informationalExpectedActivity"
                and self.determination in resolved_determinations
            )
        elif self.category == AssessmentCategory.TRUE_POSITIVE:
            valid = (
                self.status == "inProgress"
                and self.classification == "truePositive"
                and self.determination in malicious_determinations
            )
        else:
            valid = (
                self.status == "inProgress"
                and self.classification == "unknown"
                and self.determination in {"unknown", "notEnoughDataToValidate"}
            )
        if not valid:
            raise ValueError("Assessment fields do not match the selected category")
        return self
