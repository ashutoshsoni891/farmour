"""Celery task that delivers outbox events to subscribers."""

import asyncio

from app.core.events import deliver_pending
from app.db.session import get_sessionmaker
from app.jobs.celery_app import celery


async def _run() -> int:
    async with get_sessionmaker()() as session:
        count = await deliver_pending(session)
        await session.commit()
    return count


@celery.task(name="outbox.deliver")  # type: ignore[untyped-decorator]
def deliver() -> int:
    return asyncio.run(_run())
