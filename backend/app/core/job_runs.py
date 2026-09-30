"""Idempotency for scheduled jobs: a (name, run_key) pair runs at most once (spec section 3)."""

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import JobRun


async def claim(session: AsyncSession, name: str, run_key: str) -> bool:
    """Return True if this call claimed the run; False if it already ran or is running."""
    stmt = (
        insert(JobRun)
        .values(name=name, run_key=f"{name}:{run_key}")
        .on_conflict_do_nothing(index_elements=["run_key"])
        .returning(JobRun.id)
    )
    return (await session.scalar(stmt)) is not None


async def finish(session: AsyncSession, name: str, run_key: str, error: str | None = None) -> None:
    await session.execute(
        update(JobRun)
        .where(JobRun.run_key == f"{name}:{run_key}")
        .values(status="failed" if error else "done", last_error=error)
    )
