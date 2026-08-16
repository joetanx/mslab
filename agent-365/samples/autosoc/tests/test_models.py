import pytest
from pydantic import ValidationError

from models import Assessment, AssessmentCategory, AssessmentProposal, TriageRequest


def test_request_uses_strict_incident_id_contract():
    assert TriageRequest.model_validate({"incidentId": " 42 "}).incident_id == "42"
    with pytest.raises(ValidationError):
        TriageRequest.model_validate({"incidentId": "42", "extra": True})


def test_assessment_rejects_dangerous_category_field_mismatch():
    with pytest.raises(ValidationError):
        Assessment(
            category=AssessmentCategory.FALSE_POSITIVE,
            confidence=0.9,
            rationale="No evidence.",
            classification="truePositive",
            determination="malware",
            status="resolved",
        )


def test_assessment_proposal_is_mapped_to_safe_defender_fields():
    assessment = Assessment.from_proposal(
        AssessmentProposal(
            category=AssessmentCategory.SUSPICIOUS,
            confidence=0.7,
            rationale="Evidence requires analyst review.",
            determination="malware",
        )
    )

    assert assessment.classification == "unknown"
    assert assessment.determination == "unknown"
    assert assessment.status == "inProgress"