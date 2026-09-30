"""Alembic environment (async). Imports every module's models so autogenerate sees them."""

import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import app.core.models
import app.modules.farms.models
import app.modules.identity.models  # noqa: F401
from app.config import get_config
from app.db.base import Base

target_metadata = Base.metadata


def run_offline() -> None:
    context.configure(
        url=get_config().database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_online() -> None:
    engine = create_async_engine(get_config().database_url)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    asyncio.run(run_online())
