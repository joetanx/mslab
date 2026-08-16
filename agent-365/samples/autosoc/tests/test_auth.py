from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from auth import AuthenticationError, EntraTokenVerifier, get_bearer_token


TENANT_ID = "11111111-1111-1111-1111-111111111111"
AUDIENCE = "api://autosoc"
ISSUER = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"


def _token(private_key, **overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "tid": TENANT_ID,
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "oid": "logic-app-object-id",
        "azp": "logic-app-client-id",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test"})


@pytest.fixture
def verifier_and_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = EntraTokenVerifier(TENANT_ID, AUDIENCE)

    class SigningKeys:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    async def metadata():
        return ISSUER, SigningKeys()

    verifier._get_signing_metadata = metadata
    return verifier, private_key


@pytest.mark.parametrize(
    "issuer",
    [
        ISSUER,
        f"https://sts.windows.net/{TENANT_ID}/",
    ],
)
async def test_accepts_signed_tenant_and_audience_token(verifier_and_key, issuer):
    verifier, private_key = verifier_and_key

    caller = await verifier.verify(_token(private_key, iss=issuer))

    assert caller.tenant_id == TENANT_ID
    assert caller.object_id == "logic-app-object-id"
    assert caller.application_id == "logic-app-client-id"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "api://another-service"},
        {"tid": "22222222-2222-2222-2222-222222222222"},
        {"iss": "https://login.microsoftonline.com/common/v2.0"},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
    ],
)
async def test_rejects_invalid_claims(verifier_and_key, overrides):
    verifier, private_key = verifier_and_key

    with pytest.raises(AuthenticationError):
        await verifier.verify(_token(private_key, **overrides))


def test_requires_bearer_scheme():
    assert get_bearer_token("Bearer token") == "token"
    with pytest.raises(AuthenticationError):
        get_bearer_token("Basic token")
