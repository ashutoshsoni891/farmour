"""Shared pytest fixtures. Test configuration uses in-process fakes for every adapter."""

import os

os.environ.update(
    ENV="test",
    CACHE_ADAPTER="memory",
    TOKEN_VERIFIER_ADAPTER="fake",  # noqa: S106 — adapter name
    CHANNEL_ADAPTER="fake",
    STORAGE_ADAPTER="fake",
    LINK_SIGNING_SECRET="test-secret-" + "x" * 40,
    APP_BASE_URL="https://app.test",
)

pytest_plugins = ["tests.fixtures"]
