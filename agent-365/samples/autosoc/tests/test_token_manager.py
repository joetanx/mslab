from datetime import datetime, timedelta, timezone

import jwt

import token_manager


TEST_KEY = "test-key-with-at-least-32-bytes-long"


class FakeTokenProvider:
    def __init__(self, tokens):
        self.tokens = iter(tokens)
        self.calls = []

    async def get_agentic_user_token(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.tokens)


def _token(expires_in_seconds):
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    return jwt.encode({"exp": expires_at}, TEST_KEY, algorithm="HS256")


async def test_agent_user_token_is_cached_and_refreshed(monkeypatch):
    valid_token = _token(3_600)
    refreshed_token = _token(7_200)
    provider = FakeTokenProvider([valid_token, refreshed_token])
    monkeypatch.setattr(token_manager, "token_provider", provider)
    monkeypatch.setattr(token_manager, "REFRESH_BUFFER_SECONDS", 300)
    token_manager._token_cache.clear()

    arguments = {
        "tenant_id": "tenant",
        "agent_id": "agent",
        "agent_user": "user",
        "scopes": ["https://graph.microsoft.com/.default"],
    }
    first = await token_manager.get_token(**arguments)
    cached = await token_manager.get_token(**arguments)
    token_manager._token_cache.clear()
    refreshed = await token_manager.get_token(**arguments)

    assert first == cached == valid_token
    assert refreshed == refreshed_token
    assert len(provider.calls) == 2
    assert provider.calls[0]["agentic_user_id"] == "user"
