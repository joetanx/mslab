import logging, jwt
from os import environ
import time
from typing import Sequence
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager

logger = logging.getLogger(__name__)


agents_sdk_config = load_configuration_from_env(environ)
connection_manager = MsalConnectionManager(**agents_sdk_config)
token_provider = connection_manager.get_connection("SERVICE_CONNECTION")

_token_cache: dict[tuple[str | None, str | None, str | None, tuple[str] | None], str] = {}
REFRESH_BUFFER_SECONDS = int(environ.get("TOKEN_REFRESH_BUFFER_SECONDS", "300"))


async def _get_new_token(
    tenant_id: str | None = None,
    agent_id: str | None = None,
    agent_user: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> str:
    """Exchange agent user token for the specified scope and cache it."""
    token = await token_provider.get_agentic_user_token(
        tenant_id = tenant_id,
        agent_app_instance_id = agent_id,
        agentic_user_id = agent_user,
        scopes = scopes,
    )
    _cache_token(
        token=token,
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_user=agent_user,
        scopes=scopes,
    )
    return token


def _get_token_remaining_time(token: str) -> int:
    """Get the remaining time (in seconds) for the token to expire."""
    decoded_payload = jwt.decode(token, options={"verify_signature": False})
    exp_claim = decoded_payload.get("exp")
    if exp_claim:
        remaining_time = exp_claim - int(time.time())
        return max(remaining_time, 0)
    # if no expiry field in token, return 3600 seconds
    return 3600


def _cache_token(
    token: str,
    tenant_id: str | None = None,
    agent_id: str | None = None,
    agent_user: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> None:
    """Cache the token in memory for future use."""
    cache_key = (tenant_id, agent_id, agent_user, tuple(scopes) if scopes else None)
    _token_cache[cache_key] = token


async def get_token(
    tenant_id: str | None = None,
    agent_id: str | None = None,
    agent_user: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> str:
    """Retrieve a token, handling caching and refreshing transparently."""
    cache_key = (tenant_id, agent_id, agent_user, tuple(scopes) if scopes else None)
    cached_token = _token_cache.get(cache_key)
    if cached_token and _get_token_remaining_time(cached_token) > REFRESH_BUFFER_SECONDS:
        # Return the cached token if it exists and is not close to expiration
        return cached_token
    return await _get_new_token(
        # Otherwise, get a new token, the _get_new_token function will cache it for future use
        tenant_id=tenant_id,
        agent_id=agent_id,
        agent_user=agent_user,
        scopes=scopes,
    )
