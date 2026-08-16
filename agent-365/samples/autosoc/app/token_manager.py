"""Cache and refresh Agent 365 agent-user access tokens."""

import time, logging, jwt
from os import environ
from typing import Sequence
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager

logger = logging.getLogger(__name__)


agents_sdk_config = load_configuration_from_env(environ)
connection_manager = MsalConnectionManager(**agents_sdk_config)
token_provider = connection_manager.get_connection("SERVICE_CONNECTION")
_token_cache: dict[tuple[str | None, str | None, str | None, tuple[str, ...] | None], str] = {}
REFRESH_BUFFER_SECONDS = int(environ.get("TOKEN_REFRESH_BUFFER_SECONDS", "300"))


def _scope_key(scopes: Sequence[str] | str | None) -> tuple[str, ...] | None:
    if scopes is None:
        return None
    if isinstance(scopes, str):
        return (scopes,)
    return tuple(scopes)


async def _get_new_token(
    tenant_id: str | None = None,
    agent_id: str | None = None,
    agent_user: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> str:
    """Exchange agent user token for the specified scope and cache it."""
    token = await token_provider.get_agentic_user_token(
        tenant_id=tenant_id,
        agent_app_instance_id=agent_id,
        agentic_user_id=agent_user,
        scopes=scopes,
    )
    _token_cache[(tenant_id, agent_id, agent_user, _scope_key(scopes))] = token
    return token


def _get_token_remaining_time(token: str) -> int:
    """Get the remaining time (in seconds) for the token to expire."""
    payload = jwt.decode(token, options={"verify_signature": False})
    expires_at = payload.get("exp")
    if expires_at:
        remaining_time = expires_at - int(time.time())
        return max(remaining_time, 0)
    # if no expiry field in token, treat as valid token
    return REFRESH_BUFFER_SECONDS + 1


async def get_token(
    tenant_id: str | None = None,
    agent_id: str | None = None,
    agent_user: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> str:
    """Return a cached agent-user token or exchange a fresh one."""
    cache_key = (tenant_id, agent_id, agent_user, _scope_key(scopes))
    cached_token = _token_cache.get(cache_key)
    if cached_token and _get_token_remaining_time(cached_token) > REFRESH_BUFFER_SECONDS:
        # Return the cached token if it exists and is not close to expiration
        return cached_token
    return await _get_new_token(
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_user=agent_user,
        scopes=scopes,
    )
