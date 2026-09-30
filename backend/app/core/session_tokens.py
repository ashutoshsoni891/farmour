"""Caretaker session tokens issued after a single-use login link (spec sections 2 and 14).

Owners, agronomists and admins use Keycloak tokens. Caretakers have no password; after
opening a single-use link they get a signed session token from this API (PyJWT, HS256).
`session_version` on the user lets an owner or admin revoke all of a caretaker's sessions.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_config

ISSUER = "farm-api"
AUDIENCE = "farm-caretaker"


class SessionTokenError(Exception):
    pass


@dataclass(frozen=True)
class SessionClaims:
    user_id: uuid.UUID
    session_version: int


def _secret() -> str:
    secret = get_config().link_signing_secret.get_secret_value()
    if len(secret) < 32:
        raise RuntimeError("LINK_SIGNING_SECRET must be set to at least 32 characters")
    return secret


def issue(user_id: uuid.UUID, session_version: int, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": str(user_id),
        "sv": session_version,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(claims, _secret(), algorithm="HS256")


def is_session_token(token: str) -> bool:
    try:
        return jwt.get_unverified_header(token).get("alg") == "HS256"
    except jwt.PyJWTError:
        return False


def verify(token: str) -> SessionClaims:
    try:
        claims = jwt.decode(
            token,
            _secret(),
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["exp", "sub", "sv"]},
        )
        return SessionClaims(uuid.UUID(claims["sub"]), int(claims["sv"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise SessionTokenError(str(exc)) from exc
