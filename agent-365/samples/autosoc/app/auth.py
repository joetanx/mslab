"""Entra bearer-token validation for the AutoSOC webhook."""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any

import jwt
from aiohttp import ClientSession
from jwt import PyJWKClient


class AuthenticationError(Exception):
    """Raised when a request bearer token cannot be trusted."""


@dataclass(frozen=True)
class AuthenticatedCaller:
    """Selected non-sensitive claims available to request handlers."""

    tenant_id: str
    object_id: str | None
    application_id: str | None


class EntraTokenVerifier:
    """Validate signed access tokens issued by one Entra tenant and audience."""

    def __init__(
        self,
        tenant_id: str,
        audience: str,
        *,
        metadata_ttl_seconds: int = 3_600,
    ) -> None:
        self.tenant_id = tenant_id.strip()
        self.audience = audience.strip()
        if not self.tenant_id or not self.audience:
            raise ValueError("tenant_id and audience are required")

        self._metadata_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/"
            ".well-known/openid-configuration"
        )
        self._allowed_issuers = {
            f"https://sts.windows.net/{self.tenant_id}/",
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
        }
        self._metadata_ttl_seconds = metadata_ttl_seconds
        self._metadata_expires_at = 0.0
        self._issuer = ""
        self._jwks_client: PyJWKClient | None = None
        self._metadata_lock = asyncio.Lock()

    async def verify(self, token: str) -> AuthenticatedCaller:
        """Validate a JWT and return the caller claims used by the service."""
        if not token:
            raise AuthenticationError("Missing bearer token")

        try:
            _, jwks_client = await self._get_signing_metadata()
            signing_key = await asyncio.to_thread(jwks_client.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                options={"require": ["exp", "iat", "iss", "aud", "tid"]},
            )
            if claims.get("iss") not in self._allowed_issuers:
                raise AuthenticationError("Token issuer is not allowed")
            if claims.get("tid") != self.tenant_id:
                raise AuthenticationError("Token tenant is not allowed")
            return self._caller_from_claims(claims)
        except AuthenticationError:
            raise
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Bearer token validation failed") from exc
        except Exception as exc:
            raise AuthenticationError("Bearer token validation is unavailable") from exc

    async def _get_signing_metadata(self) -> tuple[str, PyJWKClient]:
        if self._jwks_client and monotonic() < self._metadata_expires_at:
            return self._issuer, self._jwks_client

        async with self._metadata_lock:
            if self._jwks_client and monotonic() < self._metadata_expires_at:
                return self._issuer, self._jwks_client

            async with ClientSession() as session:
                async with session.get(self._metadata_url, timeout=10) as response:
                    response.raise_for_status()
                    metadata = await response.json()

            issuer = metadata.get("issuer")
            jwks_uri = metadata.get("jwks_uri")
            if not isinstance(issuer, str) or not isinstance(jwks_uri, str):
                raise AuthenticationError("Invalid Entra signing metadata")

            self._issuer = issuer
            self._jwks_client = PyJWKClient(
                jwks_uri,
                cache_jwk_set=True,
                lifespan=self._metadata_ttl_seconds,
            )
            self._metadata_expires_at = monotonic() + self._metadata_ttl_seconds
            return self._issuer, self._jwks_client

    def _caller_from_claims(self, claims: Mapping[str, Any]) -> AuthenticatedCaller:
        return AuthenticatedCaller(
            tenant_id=str(claims["tid"]),
            object_id=self._optional_claim(claims, "oid"),
            application_id=(
                self._optional_claim(claims, "azp")
                or self._optional_claim(claims, "appid")
            ),
        )

    @staticmethod
    def _optional_claim(claims: Mapping[str, Any], name: str) -> str | None:
        value = claims.get(name)
        return str(value) if value is not None else None


def get_bearer_token(authorization_header: str | None) -> str:
    """Extract a bearer token without accepting alternate authorization schemes."""
    if not authorization_header:
        raise AuthenticationError("Missing Authorization header")
    scheme, separator, token = authorization_header.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError("Invalid Authorization header")
    return token.strip()