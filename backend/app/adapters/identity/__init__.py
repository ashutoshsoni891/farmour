"""Verification of identity-provider access tokens (Keycloak via OIDC)."""

from app.adapters.identity.base import TokenClaims, TokenVerifier, TokenVerifyError
from app.adapters.identity.fake import FakeTokenVerifier
from app.adapters.registry import Registry
from app.config import get_config

registry: Registry[TokenVerifier] = Registry("token_verifier")
registry.register("fake", FakeTokenVerifier)


def _keycloak() -> TokenVerifier:
    from app.adapters.identity.keycloak import KeycloakTokenVerifier

    cfg = get_config()
    return KeycloakTokenVerifier(
        jwks_url=cfg.keycloak_jwks_url, issuer=cfg.keycloak_issuer, client_id=cfg.keycloak_client_id
    )


registry.register("keycloak", _keycloak)


def get_token_verifier() -> TokenVerifier:
    return registry.get(get_config().token_verifier_adapter)


__all__ = ["TokenClaims", "TokenVerifier", "TokenVerifyError", "get_token_verifier", "registry"]
