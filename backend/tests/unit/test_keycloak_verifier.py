import json
import time
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.adapters.identity.base import TokenVerifyError
from app.adapters.identity.keycloak import KeycloakTokenVerifier

ISSUER = "https://auth.test/realms/farm"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks() -> dict[str, Any]:
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key()))
    jwk.update(kid="k1", use="sig", alg="RS256")
    return {"keys": [jwk]}


def _verifier() -> KeycloakTokenVerifier:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=_jwks()))
    return KeycloakTokenVerifier("https://auth.test/certs", ISSUER, "farm-web", transport)


def _token(**overrides: Any) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": "abc",
        "azp": "farm-web",
        "iat": now,
        "exp": now + 60,
        "email": "o@example.test",
        "realm_access": {"roles": ["x"]},
    }
    claims.update(overrides)
    kid = claims.pop("_kid", "k1")
    return jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": kid})


async def test_valid_token() -> None:
    claims = await _verifier().verify(_token())
    assert claims.subject == "abc"
    assert claims.email == "o@example.test"
    assert claims.roles == frozenset({"x"})


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://evil.test/realms/farm"},
        {"azp": "other-client"},
        {"exp": int(time.time()) - 10},
        {"_kid": "unknown"},
    ],
)
async def test_bad_tokens_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(TokenVerifyError):
        await _verifier().verify(_token(**overrides))


async def test_hs256_token_with_public_key_rejected() -> None:
    forged = jwt.encode(
        {"iss": ISSUER, "sub": "abc", "azp": "farm-web"},
        "k",
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    with pytest.raises(TokenVerifyError):
        await _verifier().verify(forged)


async def test_idp_unreachable_is_a_verify_error() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(503))
    v = KeycloakTokenVerifier("https://auth.test/certs", ISSUER, "farm-web", transport)
    with pytest.raises(TokenVerifyError):
        await v.verify(_token())
