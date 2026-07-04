"""Token caching utilities for Agent 365 authentication flows."""

import base64
import json
import logging
import time

logger = logging.getLogger(__name__)

# Global token cache for Agent 365 authentication tokens.
_token_cache: dict[str, str] = {}
_TOKEN_REFRESH_BUFFER_SECONDS = 300


def _decode_jwt_payload(token: str) -> dict | None:
    """Decode JWT claims without validating the signature."""
    parts = token.split(".")
    if len(parts) < 2:
        return None

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")))
    except (ValueError, json.JSONDecodeError):
        return None


def is_token_valid(token: str | None) -> bool:
    """Return whether a cached JWT is still usable."""
    if not token:
        return False

    payload = _decode_jwt_payload(token)
    if payload is None:
        logger.debug("Treating opaque token as valid because no JWT payload was found")
        return True

    expires_at = payload.get("exp")
    if not isinstance(expires_at, (int, float)):
        logger.debug("Treating token without exp claim as valid")
        return True

    return expires_at > time.time() + _TOKEN_REFRESH_BUFFER_SECONDS


def cache_token(cache_key: str, token: str) -> None:
    """Cache a token until it is expired or near expiry."""
    _token_cache[cache_key] = token
    logger.debug("Cached token for %s", cache_key)


def get_cached_token(cache_key: str) -> str | None:
    """Retrieve a cached token when it is still valid."""
    token = _token_cache.get(cache_key)
    if not token:
        logger.debug("No cached token found for %s", cache_key)
        return None

    if not is_token_valid(token):
        logger.debug("Cached token for %s is expired or near expiry", cache_key)
        _token_cache.pop(cache_key, None)
        return None

    logger.debug("Retrieved cached token for %s", cache_key)
    return token


def build_token_cache_key(*parts: object) -> str:
    """Build a stable cache key from identity and scope parts."""
    return ":".join(str(part or "") for part in parts)


def cache_agentic_token(tenant_id: str, agent_id: str, token: str) -> None:
    """Cache the agentic token for use by Agent 365 Observability exporter."""
    cache_token(build_token_cache_key("observability", tenant_id, agent_id), token)


def get_cached_agentic_token(tenant_id: str, agent_id: str) -> str | None:
    """Retrieve cached agentic token for Agent 365 Observability exporter."""
    return get_cached_token(build_token_cache_key("observability", tenant_id, agent_id))
