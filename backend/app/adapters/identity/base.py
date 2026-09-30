from dataclasses import dataclass, field
from typing import Protocol


class TokenVerifyError(Exception):
    """The token is missing, malformed, expired or not issued for this app."""


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None
    roles: frozenset[str] = field(default_factory=frozenset)


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> TokenClaims: ...
