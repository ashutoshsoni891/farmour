import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

import app.core.models
import app.modules.farms.models
import app.modules.identity.models  # noqa: F401
from app.db.base import Base
from tests.fixtures import alembic_config

pytestmark = pytest.mark.integration


def test_downgrade_and_upgrade_again(migrated: str) -> None:
    cfg = alembic_config(migrated)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def test_models_match_migrations(migrated: str) -> None:
    """Fails if a model changed without a migration (or the reverse)."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    async def diff() -> list[object]:
        engine = create_async_engine(migrated)
        async with engine.connect() as conn:
            result = await conn.run_sync(
                lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata)
            )
        await engine.dispose()
        return list(result)

    changes = [c for c in asyncio.run(diff()) if "spatial_ref_sys" not in str(c)]
    assert changes == []


def test_extensions_and_seeds(migrated: str) -> None:
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def check() -> tuple[set[str], int, int]:
        engine = create_async_engine(migrated)
        async with engine.connect() as conn:
            ext: set[str] = set(
                (await conn.execute(text("select extname from pg_extension"))).scalars()
            )
            regions = await conn.scalar(text("select count(*) from regions where slug='malwa'"))
            settings = await conn.scalar(text("select count(*) from settings"))
        await engine.dispose()
        return ext, int(regions or 0), int(settings or 0)

    ext, regions, settings = asyncio.run(check())
    assert {"postgis", "vector"} <= ext
    assert regions == 1
    assert settings >= 4
