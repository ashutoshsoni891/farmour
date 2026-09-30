"""Process configuration from environment variables (12-factor).

Only deployment wiring lives here (URLs, secrets, which adapter to use). Tunable product
numbers live in the `settings` table (see app.core.settings_store).
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["local", "test", "staging", "prod"] = "local"
    app_base_url: str = "http://localhost"
    cors_origins: list[str] = ["http://localhost"]

    database_url: str = "postgresql+asyncpg://farm:farm@localhost:5432/farm"
    valkey_url: str = "redis://localhost:6379/0"

    keycloak_url: str = "http://localhost:8080"
    keycloak_public_url: str | None = None  # issuer host seen by browsers, if different
    keycloak_realm: str = "farm"
    keycloak_client_id: str = "farm-web"

    link_signing_secret: SecretStr = SecretStr("")

    s3_endpoint: str = "http://localhost:8333"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    s3_bucket: str = "farm-files"

    telegram_bot_token: SecretStr = SecretStr("")
    telegram_webhook_secret: SecretStr = SecretStr("")

    glitchtip_dsn: str = ""
    settings_cache_seconds: int = 300

    # Adapter selection (registry keys). Fakes are used in tests.
    cache_adapter: str = "valkey"
    storage_adapter: str = "s3"
    token_verifier_adapter: str = "keycloak"  # noqa: S105 — adapter name, not a secret
    channel_adapter: str = "fake"  # telegram arrives in M5

    @property
    def keycloak_issuer(self) -> str:
        base = self.keycloak_public_url or self.keycloak_url
        return f"{base.rstrip('/')}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        base = self.keycloak_url.rstrip("/")
        return f"{base}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


@lru_cache
def get_config() -> Config:
    return Config()
