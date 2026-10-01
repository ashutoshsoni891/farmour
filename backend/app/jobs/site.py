"""Celery tasks for site intelligence."""

import asyncio
import uuid
from typing import Any

from app.db.session import standalone_session
from app.jobs.celery_app import celery
from app.modules.site import service


async def _build(farm_id: str) -> dict[str, Any]:
    async with standalone_session() as session:
        result = await service.build_profile(session, uuid.UUID(farm_id))
        await session.commit()
    return result


async def _ingest() -> dict[str, Any]:
    async with standalone_session() as session:
        result = await service.ingest_mandi_prices(session)
        await session.commit()
    return result


@celery.task(name="site.build_profile")  # type: ignore[untyped-decorator]
def build_profile(farm_id: str) -> dict[str, Any]:
    return asyncio.run(_build(farm_id))


@celery.task(name="site.ingest_mandi_prices")  # type: ignore[untyped-decorator]
def ingest_mandi_prices() -> dict[str, Any]:
    return asyncio.run(_ingest())
