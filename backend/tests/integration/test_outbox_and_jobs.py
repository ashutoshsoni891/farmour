import uuid
from dataclasses import dataclass, field

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import events, job_runs
from app.core.models import JobRun, OutboxEvent

pytestmark = pytest.mark.integration


@dataclass
class Subscribers:
    event: str
    calls: list[tuple[str, uuid.UUID]] = field(default_factory=list)


@pytest.fixture
def subs() -> Subscribers:
    """An 'ok' subscriber and a 'flaky' one that fails on its first call."""
    s = Subscribers(event=f"test.event.{uuid.uuid4().hex[:8]}")
    failures_left = [1]

    @events.subscribe(s.event, "ok")
    async def ok(_: AsyncSession, e: events.Event) -> None:
        s.calls.append(("ok", e.id))

    @events.subscribe(s.event, "flaky")
    async def flaky(_: AsyncSession, e: events.Event) -> None:
        if failures_left[0]:
            failures_left[0] -= 1
            raise RuntimeError("temporary")
        s.calls.append(("flaky", e.id))

    return s


async def test_publish_is_part_of_the_callers_transaction(session: AsyncSession) -> None:
    tx = await session.begin_nested()
    event_id = await events.publish(session, "test.rollback", {"x": 1})
    await tx.rollback()
    assert await session.get(OutboxEvent, event_id) is None


async def test_each_subscriber_runs_once_and_failures_retry(
    session: AsyncSession, subs: Subscribers
) -> None:
    event_id = await events.publish(session, subs.event, {"id": "1"})

    await events.deliver_pending(session)
    row = await session.get(OutboxEvent, event_id)
    assert row is not None
    assert row.delivered_at is None
    assert row.delivered_to == ["ok"]
    assert row.attempts == 1

    row.next_attempt_at = row.created_at  # due again now
    await session.flush()
    await events.deliver_pending(session)
    await session.refresh(row)
    assert row.delivered_at is not None
    assert subs.calls == [("ok", event_id), ("flaky", event_id)]  # ok did not run twice


async def test_job_claimed_once(session: AsyncSession) -> None:
    key = uuid.uuid4().hex
    assert await job_runs.claim(session, "daily_tasks", key) is True
    assert await job_runs.claim(session, "daily_tasks", key) is False
    await job_runs.finish(session, "daily_tasks", key)
    runs = await session.get(JobRun, await _job_id(session, f"daily_tasks:{key}"))
    assert runs is not None
    assert runs.status == "done"


async def _job_id(session: AsyncSession, run_key: str) -> uuid.UUID:
    from sqlalchemy import select

    job_id = await session.scalar(select(JobRun.id).where(JobRun.run_key == run_key))
    assert job_id is not None
    return job_id
