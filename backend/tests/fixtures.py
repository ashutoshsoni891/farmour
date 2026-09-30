"""Integration fixtures: a real Postgres + PostGIS + pgvector in Docker (testcontainers).

Set TEST_DATABASE_URL to reuse an existing database instead of starting a container.
Each test runs inside a transaction that is rolled back afterwards.
"""

import os
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine

from app.adapters import cache, channel, identity
from app.adapters.cache.memory import MemoryCache
from app.adapters.channel.fake import FakeChannel
from app.adapters.identity import TokenClaims
from app.adapters.identity.fake import FakeTokenVerifier
from app.config import get_config
from app.core import settings_store

BACKEND = Path(__file__).resolve().parents[1]
DB_IMAGE_DIR = BACKEND.parent / "deploy" / "postgres"


def alembic_config(url: str) -> AlembicConfig:
    cfg = AlembicConfig(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "app/db/migrations"))
    os.environ["DATABASE_URL"] = url
    get_config.cache_clear()
    return cfg


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    from testcontainers.core.image import DockerImage
    from testcontainers.postgres import PostgresContainer

    with (
        DockerImage(path=str(DB_IMAGE_DIR), tag="farm-postgres:test") as image,
        PostgresContainer(str(image), driver="asyncpg") as pg,
    ):
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def migrated(database_url: str) -> str:
    cfg = alembic_config(database_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return database_url


@pytest.fixture(scope="session")
async def engine(migrated: str) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(migrated)
    yield eng
    await eng.dispose()


@pytest.fixture
async def conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        trans = await connection.begin()
        yield connection
        await trans.rollback()


@pytest.fixture
async def session(conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    s = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield s
    await s.close()


@pytest.fixture
def fakes() -> Iterator["Fakes"]:
    f = Fakes(verifier=FakeTokenVerifier(), channel=FakeChannel(), cache=MemoryCache())
    identity.registry.override("fake", f.verifier)
    channel.registry.override("fake", f.channel)
    cache.registry.override("memory", f.cache)
    settings_store.clear_cache()
    yield f
    settings_store.clear_cache()


@dataclass
class Fakes:
    verifier: FakeTokenVerifier
    channel: FakeChannel
    cache: MemoryCache

    def keycloak_token(self, email: str | None = None) -> str:
        """A token as if issued by Keycloak for a new identity."""
        sub = str(uuid.uuid4())
        return self.verifier.issue(TokenClaims(subject=sub, email=email or f"{sub}@example.test"))


@pytest.fixture
async def client(session: AsyncSession, fakes: Fakes) -> AsyncIterator[AsyncClient]:
    from app.db.session import get_session
    from app.main import create_app

    app = create_app()

    async def _session() -> AsyncIterator[AsyncSession]:
        yield session
        await session.flush()

    app.dependency_overrides[get_session] = _session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
