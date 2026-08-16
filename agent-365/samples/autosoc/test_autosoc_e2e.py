import sys
import asyncio
from typing import Any, Dict, List
from os import environ

# Set up paths
sys.path.append(r"c:\Users\Eisen\Documents\GitHub\mslab\agent-365\samples\autosoc\app")

# Set up environment variables that might be expected
environ["MAX_HUNTS_PER_INCIDENT"] = "5"
environ["TRIAGE_TIMEOUT_SECONDS"] = "300"
environ["ASSIGNEE_RESOLVED"] = "resolved_user"
environ["ASSIGNEE_IN_PROGRESS"] = "inprogress_user"

from models import (
    ContextExtraction,
    EntityCollection,
    HuntSelection,
    HuntPlan,
    AssessmentProposal,
    AssessmentCategory,
)
from agent import AutoSOCAgent

class FakeStructuredOutputModel:
    def __init__(self, expected_type):
        self.expected_type = expected_type

    async def ainvoke(self, prompt: str, *args, **kwargs):
        if self.expected_type == ContextExtraction:
            return ContextExtraction(
                overview="This is a test incident overview.",
                entities=EntityCollection(
                    ip_addresses=["10.0.0.1"],
                    domains=[],
                    urls=[],
                    file_hashes=[],
                    hostnames=["test-host"],
                    users=[],
                    upns=["user@domain.com"]
                )
            )
        elif self.expected_type == HuntSelection:
            return HuntSelection(
                hunts=[
                    HuntPlan(hunt_id="threat_intelligence", rationale="suspicious IP and host"),
                    HuntPlan(hunt_id="entra_sign_in", rationale="suspicious UPN signin")
                ]
            )
        elif self.expected_type == AssessmentProposal:
            return AssessmentProposal(
                category=AssessmentCategory.SUSPICIOUS,
                confidence=0.8,
                rationale="Suspicious indicators require analyst triage.",
                determination="unknown"
            )
        else:
            raise ValueError(f"Unknown expected type: {self.expected_type}")

class MockModel:
    def with_structured_output(self, schema, **kwargs):
        return FakeStructuredOutputModel(schema)

class MockGraphClient:
    def __init__(self):
        self.calls = []
        self.incidents = {}
        self.comments = []
        self.updates = []

    async def get_incident(self, incident_id: str) -> dict:
        self.calls.append(("get_incident", incident_id))
        return {"display_name": "Test incident", "severity": "Medium"}

    async def list_incident_alerts(self, incident_id: str) -> list:
        self.calls.append(("list_incident_alerts", incident_id))
        return [{"id": "alert1", "title": "Suspicious Activity"}]

    async def run_hunting_query(self, query: str, timespan: str, *, result_limit: int = 100) -> list:
        self.calls.append(("run_hunting_query", query, timespan))
        if "threat_intelligence" in query or "threat" in query.lower():
            row = {'Modified': '2026-08-16', 'ObservableKey': 'IP', 'ObservableValue': '10.0.0.1', 'IsActive': 'True', 'Confidence': 'High'}
        else:
            row = {'Identity': 'user@domain.com', 'UserPrincipalName': 'user@domain.com', 'FailureCount': '1', 'LastSeen': '2026-08-16', 'ResultDescriptions': 'Success', 'IPAddresses': '10.0.0.1'}
        return [row]

    async def add_incident_comment(self, incident_id: str, comment: str) -> None:
        self.calls.append(("add_incident_comment", incident_id, comment))
        self.comments.append(comment)

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
        self.calls.append(("update_incident", incident_id, status, classification, determination, assigned_to, resolving_comment))
        self.updates.append({
            "incident_id": incident_id,
            "status": status,
            "classification": classification,
            "determination": determination,
            "assigned_to": assigned_to,
            "resolving_comment": resolving_comment
        })

    async def close(self) -> None:
        pass

async def test_e2e():
    mock_model = MockModel()
    mock_graph_client = MockGraphClient()
    agent = AutoSOCAgent(model=mock_model, graph_client=mock_graph_client)

    incident_id = "inc_123"
    correlation_id = "corr_456"

    # Verify checkpointer is empty
    print("Initial checkpointer threads:", list(agent._checkpointer.storage.keys()))

    # Run triage
    await agent.run_triage(incident_id=incident_id, correlation_id=correlation_id)
    print("run_triage completed successfully!")

    # Verify both hunts execute
    queries_run = [c for c in mock_graph_client.calls if c[0] == "run_hunting_query"]
    print(f"Hunts run count: {len(queries_run)}")
    for q in queries_run:
        print(f" - Query: {q[1][:120]}...")

    failures = []
    if len(queries_run) != 2:
        failures.append(f"Expected exactly 2 hunting queries, but got {len(queries_run)}")

    # Verify exactly one consolidated comment and one update occur
    print(f"Comments: {len(mock_graph_client.comments)}")
    if len(mock_graph_client.comments) != 1:
        failures.append(f"Expected exactly 1 comment, but got {len(mock_graph_client.comments)}")
    else:
        print("Comment content:")
        print(mock_graph_client.comments[0])

    print(f"Updates: {len(mock_graph_client.updates)}")
    if len(mock_graph_client.updates) != 1:
        failures.append(f"Expected exactly 1 update, but got {len(mock_graph_client.updates)}")
    else:
        print("Update detail:", mock_graph_client.updates[0])

    # Check checkpointer storage no longer contains the correlation ID
    print("After triage checkpointer threads:", list(agent._checkpointer.storage.keys()))
    if correlation_id in agent._checkpointer.storage:
        failures.append(f"Correlation ID {correlation_id} is still in checkpointer storage!")

    if failures:
        print("FAILURES DETECTED:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    else:
        print("ALL VERIFICATIONS PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(test_e2e())
