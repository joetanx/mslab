"""Exchange and cache agentic access tokens."""

import asyncio
import base64
import binascii
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from os import environ
from typing import Any


REFRESH_BUFFER_SECONDS = int(environ.get("TOKEN_REFRESH_BUFFER_SECONDS", "300"))


@dataclass(frozen=True)
class CachedToken:
    value: str
    expires_at: float


_cache: dict[tuple[str | None, str, tuple[str, ...]], CachedToken] = {}
_locks: dict[tuple[str | None, str, tuple[str, ...]], asyncio.Lock] = {}


def get_cached_token(
    *,
    agent_id: str | None,
    tenant_id: str | None = None,
    scopes: Sequence[str] | str | None = None,
) -> str:
    """Return a usable cached token, or an empty string."""
    if not agent_id:
        return ""

    key = (tenant_id, agent_id, _normalize_scopes(scopes))
    cached = _cache.get(key)
    if not cached or cached.expires_at - time.time() <= REFRESH_BUFFER_SECONDS:
        return ""
    return cached.value


async def exchange_token(
    *,
    agent_id: str | None,
    tenant_id: str | None,
    auth: Any,
    auth_handler_name: str | None,
    context: Any,
    scopes: Sequence[str] | str | None,
) -> str:
    """Return a cached token or exchange and cache a new one."""
    normalized_scopes = _normalize_scopes(scopes)
    cached = get_cached_token(
        agent_id=agent_id, tenant_id=tenant_id, scopes=normalized_scopes
    )
    if cached:
        return cached
    if not agent_id or not auth_handler_name:
        return ""

    key = (tenant_id, agent_id, normalized_scopes)
    async with _locks.setdefault(key, asyncio.Lock()):
        cached = get_cached_token(
            agent_id=agent_id, tenant_id=tenant_id, scopes=normalized_scopes
        )
        if cached:
            return cached

        result = await auth.exchange_token(
            context,
            scopes=list(normalized_scopes),
            auth_handler_id=auth_handler_name,
        )
        value = result if isinstance(result, str) else getattr(result, "token", "")
        if not value:
            raise ValueError("Token exchange did not return a token")

        _cache[key] = CachedToken(value=value, expires_at=_expires_at(result, value))
        return value


def _normalize_scopes(scopes: Sequence[str] | str | None) -> tuple[str, ...]:
    if scopes is None:
        return ()
    if isinstance(scopes, str):
        return (scopes,)
    return tuple(scopes)


def _expires_at(result: Any, token: str) -> float:
    for name in ("expires_on", "expires_at"):
        value = getattr(result, name, None)
        if isinstance(value, int | float):
            return float(value)

    for name in ("expires_in", "expires_in_seconds"):
        value = getattr(result, name, None)
        if isinstance(value, int | float):
            return time.time() + float(value)

    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        expiry = json.loads(base64.urlsafe_b64decode(payload))["exp"]
        return float(expiry)
    except (
        binascii.Error,
        IndexError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return time.time() + 3600
