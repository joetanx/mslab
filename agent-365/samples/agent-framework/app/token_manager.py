"""Caches and exchanges agentic tokens for authenticated agent calls."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from os import environ
from typing import Any

logger = logging.getLogger(__name__)

TOKEN_REFRESH_BUFFER_SECONDS = int(environ.get("TOKEN_REFRESH_BUFFER_SECONDS", "300"))


@dataclass(frozen=True)
class CachedToken:
    """Stores a cached token and the metadata needed to validate it."""

    token: str
    expires_at: float
    scopes: tuple[str, ...]
    tenant_id: str | None

    def is_valid_for(self, scopes: tuple[str, ...]) -> bool:
        """Return whether the cached token is valid for the requested scopes."""
        if self.scopes and scopes and self.scopes != scopes:
            return False
        return self.expires_at - time.time() > TOKEN_REFRESH_BUFFER_SECONDS


_agentic_token_cache: dict[str, CachedToken] = {}
_agent_locks: dict[str, asyncio.Lock] = {}


def get_token(
    *,
    agent_id: str | None,
    tenant_id: str | None = None,
    auth: Any | None = None,
    auth_handler_name: str | None = None,
    context: Any | None = None,
    scopes: Sequence[str] | str | None = None,
):
    """Return a cached token or start an authenticated token exchange."""
    normalized_scopes = _normalize_scopes(scopes)
    if auth is not None and context is not None:
        return _get_token_async(
            agent_id=agent_id,
            tenant_id=tenant_id,
            auth=auth,
            auth_handler_name=auth_handler_name,
            context=context,
            scopes=normalized_scopes,
        )

    return _get_cached_token(agent_id, tenant_id, normalized_scopes) or ""


def token_is_valid(
    *,
    agent_id: str | None,
    tenant_id: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> bool:
    """Return whether a non-expiring cached token exists for the agent and scopes."""
    normalized_scopes = _normalize_scopes(scopes)
    return _get_cached_token(agent_id, tenant_id, normalized_scopes) is not None


async def _get_token_async(
    *,
    agent_id: str | None,
    tenant_id: str | None,
    auth: Any,
    auth_handler_name: str | None,
    context: Any,
    scopes: tuple[str, ...],
) -> str:
    """Exchange and cache an agentic token when no valid cached token exists."""
    cached_token = _get_cached_token(agent_id, tenant_id, scopes)
    if cached_token:
        return cached_token

    if not agent_id:
        logger.warning("Cannot exchange token without agent_id")
        return ""

    if not auth_handler_name:
        logger.debug("Skipping token exchange because no auth handler is configured")
        return ""

    cache_key = _get_cache_key(agent_id, tenant_id, scopes)
    lock = _agent_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        cached_token = _get_cached_token(agent_id, tenant_id, scopes)
        if cached_token:
            return cached_token

        logger.info(
            "Exchanging agentic token (tenant_id=%s, agent_id=%s)",
            tenant_id or "(unknown)",
            agent_id,
        )
        exchanged_token = await auth.exchange_token(
            context,
            scopes=list(scopes),
            auth_handler_id=auth_handler_name,
        )
        token = _extract_token_value(exchanged_token)
        expires_at = _extract_expires_at(exchanged_token, token)
        _agentic_token_cache[cache_key] = CachedToken(
            token=token,
            expires_at=expires_at,
            scopes=scopes,
            tenant_id=tenant_id,
        )
        logger.info(
            "Cached agentic token (tenant_id=%s, agent_id=%s, expires_in=%ss)",
            tenant_id or "(unknown)",
            agent_id,
            max(0, int(expires_at - time.time())),
        )
        return token


def cache_agentic_token(
    tenant_id: str | None,
    agent_id: str,
    token: str,
    scopes: Sequence[str] | str | None = None,
) -> None:
    """Store an agentic token in the in-memory cache."""
    normalized_scopes = _normalize_scopes(scopes)
    cache_key = _get_cache_key(agent_id, tenant_id, normalized_scopes)
    _agentic_token_cache[cache_key] = CachedToken(
        token=token,
        expires_at=_extract_expires_at(None, token),
        scopes=normalized_scopes,
        tenant_id=tenant_id,
    )
    logger.debug("Cached agentic token for agent_id=%s", agent_id)


def get_cached_agentic_token(tenant_id: str | None, agent_id: str) -> str | None:
    """Return the cached agentic token for a tenant and agent if available."""
    token = get_token(agent_id=agent_id, tenant_id=tenant_id)
    return token or None


def _get_cached_token(agent_id: str | None, tenant_id: str | None, scopes: tuple[str, ...]) -> str | None:
    """Return a valid cached token for an agent and scope set."""
    if not agent_id:
        logger.warning("Cannot resolve cached token without agent_id")
        return None

    cache_key = _get_cache_key(agent_id, tenant_id, scopes)
    cached_token = _agentic_token_cache.get(cache_key)
    if not cached_token:
        logger.debug("No cached token found for agent_id=%s", agent_id)
        return None

    if not cached_token.is_valid_for(scopes):
        logger.info("Cached token needs refresh for agent_id=%s", agent_id)
        return None

    logger.debug("Using cached token for agent_id=%s", agent_id)
    return cached_token.token


def _get_cache_key(agent_id: str, tenant_id: str | None, scopes: tuple[str, ...]) -> str:
    """Build a cache key that isolates tenants and token audiences."""
    scope_key = " ".join(scopes)
    return f"{tenant_id or ''}:{agent_id}:{scope_key}"


def _normalize_scopes(scopes: Sequence[str] | str | None) -> tuple[str, ...]:
    """Normalize scope input into a tuple of strings."""
    if scopes is None:
        return ()
    if isinstance(scopes, str):
        return (scopes,)
    return tuple(scopes)


def _extract_token_value(exchanged_token: Any) -> str:
    """Extract the raw token string from an exchange result."""
    if isinstance(exchanged_token, str):
        return exchanged_token

    token = getattr(exchanged_token, "token", None)
    if isinstance(token, str) and token:
        return token

    raise ValueError("Token exchange did not return a token value")


def _extract_expires_at(exchanged_token: Any, token: str) -> float:
    """Resolve the absolute expiration time for an exchanged token."""
    now = time.time()

    for attr in ("expires_on", "expires_at"):
        expires_at = getattr(exchanged_token, attr, None)
        if isinstance(expires_at, int | float):
            return float(expires_at)

    for attr in ("expires_in", "expires_in_seconds"):
        expires_in = getattr(exchanged_token, attr, None)
        if isinstance(expires_in, int | float):
            return now + float(expires_in)

    jwt_expires_at = _decode_jwt_exp(token)
    if jwt_expires_at is not None:
        return jwt_expires_at

    # Set expire to longer than buffer if token doesn't have expiry
    return now + TOKEN_REFRESH_BUFFER_SECONDS


def _decode_jwt_exp(token: str) -> float | None:
    """Decode the expiration claim from a JWT token."""
    parts = token.split(".")
    if len(parts) < 2:
        return None

    payload = parts[1]
    padded_payload = payload + "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded_payload.encode("ascii"))
        claims = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None

    exp = claims.get("exp")
    if isinstance(exp, int | float):
        return float(exp)
    return None
