"""Async engine and session. One session per request; the request commits once at the end."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_config


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_config().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session and commits if the request succeeded."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


@asynccontextmanager
async def standalone_session() -> AsyncIterator[AsyncSession]:
    """A session with its own unpooled engine, for code that runs each job in a fresh event
    loop (Celery tasks via asyncio.run). Pooled connections cannot cross event loops."""
    engine = create_async_engine(get_config().database_url, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()
