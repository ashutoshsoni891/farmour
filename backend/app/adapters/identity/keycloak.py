"""Keycloak access-token verification (RS256 via the realm JWKS). No token issuing here."""

import time
from typing import Any

import httpx
import jwt

from app.adapters.identity.base import TokenClaims, TokenVerifyError

_JWKS_TTL_SECONDS = 600


class KeycloakTokenVerifier:
    def __init__(
        self,
        jwks_url: str,
        issuer: str,
        client_id: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._jwks_url = jwks_url
        self._transport = transport
        self._issuer = issuer
        self._client_id = client_id
        self._keys: dict[str, Any] = {}
        self._fetched_at = 0.0

    async def _refresh(self) -> None:
        async with httpx.AsyncClient(timeout=5, transport=self._transport) as client:
            resp = await client.get(self._jwks_url)
            resp.raise_for_status()
        jwks = jwt.PyJWKSet.from_dict(resp.json())
        self._keys = {k.key_id: k.key for k in jwks.keys if k.key_id}
        self._fetched_at = time.monotonic()

    async def _key_for(self, kid: str) -> Any:
        stale = time.monotonic() - self._fetched_at > _JWKS_TTL_SECONDS
        if kid not in self._keys or stale:
            try:
                await self._refresh()
            except (httpx.HTTPError, jwt.PyJWKError) as exc:
                raise TokenVerifyError("identity provider keys unavailable") from exc
        try:
            return self._keys[kid]
        except KeyError:
            raise TokenVerifyError("unknown signing key") from None

    async def verify(self, token: str) -> TokenClaims:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            if not kid:
                raise TokenVerifyError("token has no key id")
            key = await self._key_for(kid)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub", "iss"], "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise TokenVerifyError(str(exc)) from exc
        # Keycloak access tokens carry the client in `azp`; `aud` is often "account".
        if claims.get("azp") != self._client_id:
            raise TokenVerifyError("token not issued for this client")
        roles = frozenset(claims.get("realm_access", {}).get("roles", []))
        return TokenClaims(
            subject=str(claims["sub"]),
            email=claims.get("email"),
            name=claims.get("name"),
            roles=roles,
        )
