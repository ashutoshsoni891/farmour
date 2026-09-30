"""Test verifier: accepts tokens registered with `issue`, nothing else."""

import secrets

from app.adapters.identity.base import TokenClaims, TokenVerifyError


class FakeTokenVerifier:
    def __init__(self) -> None:
        self._tokens: dict[str, TokenClaims] = {}

    def issue(self, claims: TokenClaims) -> str:
        token = "fake." + secrets.token_urlsafe(16)
        self._tokens[token] = claims
        return token

    async def verify(self, token: str) -> TokenClaims:
        try:
            return self._tokens[token]
        except KeyError:
            raise TokenVerifyError("unknown token") from None
