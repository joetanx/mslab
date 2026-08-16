from datetime import datetime, timedelta, timezone

import jwt

import graph_tools


TEST_KEY = "test-key-with-at-least-32-bytes-long"


def _token(marker):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return jwt.encode(
        {"exp": expires_at, "marker": marker}, TEST_KEY, algorithm="HS256"
    )


async def test_graph_client_rebuilds_when_agent_user_token_rotates(monkeypatch):
    tokens = iter([_token("first"), _token("first"), _token("second")])
    created_credentials = []

    async def fake_get_token(**kwargs):
        assert kwargs == {
            "tenant_id": "tenant",
            "agent_id": "agent",
            "agent_user": "user",
            "scopes": ["https://graph.microsoft.com/.default"],
        }
        return next(tokens)

    class FakeGraphClient:
        def __init__(self, credentials):
            created_credentials.append(credentials)

    monkeypatch.setenv("CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID", "tenant")
    monkeypatch.setenv("AGENTIC_INSTANCE_ID", "agent")
    monkeypatch.setenv("AGENTIC_USER_ID", "user")
    monkeypatch.setattr(graph_tools, "get_token", fake_get_token)
    monkeypatch.setattr(graph_tools, "GraphServiceClient", FakeGraphClient)
    client = graph_tools.GraphSecurityClient()

    first = await client._get_client()
    cached = await client._get_client()
    refreshed = await client._get_client()

    assert first is cached
    assert refreshed is not first
    assert len(created_credentials) == 2


async def test_add_incident_comment_enforces_graph_limit():
    posted = []

    class CommentsRequestBuilder:
        async def post(self, request_body):
            posted.append(request_body.comment)

    class IncidentsRequestBuilder:
        def with_url(self, url):
            assert url.endswith("/security/incidents/incident-1/comments")
            return CommentsRequestBuilder()

    class SecurityRequestBuilder:
        incidents = IncidentsRequestBuilder()

    class FakeGraphClient:
        security = SecurityRequestBuilder()

    client = graph_tools.GraphSecurityClient(graph_client=FakeGraphClient())

    await client.add_incident_comment("incident-1", "x" * 1_312)

    assert posted == ["x" * graph_tools.INCIDENT_COMMENT_MAX_LENGTH]