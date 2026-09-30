"""Domain events via the transactional outbox (spec section 16).

`publish` inserts an outbox row in the caller's transaction. A worker calls `deliver_pending`,
which hands each event to its subscribers. Events carry IDs and a version, never whole objects.
Each subscriber runs at most once per successful delivery (tracked in `delivered_to`), so a
subscriber that failed is retried without re-running the ones that succeeded.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import OutboxEvent

log = structlog.get_logger()


@dataclass(frozen=True)
class Event:
    id: uuid.UUID
    name: str
    version: int
    payload: dict[str, Any]


Handler = Callable[[AsyncSession, Event], Awaitable[None]]
_subscribers: dict[str, dict[str, Handler]] = {}

MAX_ATTEMPTS = 10


def subscribe(event: str, name: str) -> Callable[[Handler], Handler]:
    """Register `handler` under a stable subscriber `name` for `event`."""

    def deco(handler: Handler) -> Handler:
        subs = _subscribers.setdefault(event, {})
        if name in subs:
            raise ValueError(f"subscriber {name!r} already registered for {event!r}")
        subs[name] = handler
        return handler

    return deco


def subscribers(event: str) -> dict[str, Handler]:
    return dict(_subscribers.get(event, {}))


async def publish(
    session: AsyncSession, event: str, payload: dict[str, Any], *, version: int = 1
) -> uuid.UUID:
    row = OutboxEvent(id=uuid.uuid4(), event=event, version=version, payload=payload)
    session.add(row)
    await session.flush()
    return row.id


def _backoff(attempts: int) -> timedelta:
    return timedelta(seconds=min(2**attempts * 5, 3600))


async def deliver_pending(session: AsyncSession, *, batch: int = 50) -> int:
    """Deliver due events; returns how many were fully delivered. Caller commits."""
    now = datetime.now(UTC)
    rows = (
        await session.scalars(
            select(OutboxEvent)
            .where(
                OutboxEvent.delivered_at.is_(None),
                OutboxEvent.next_attempt_at <= now,
                OutboxEvent.attempts < MAX_ATTEMPTS,
            )
            .order_by(OutboxEvent.created_at)
            .limit(batch)
            .with_for_update(skip_locked=True)
        )
    ).all()
    delivered = 0
    for row in rows:
        event = Event(row.id, row.event, row.version, row.payload)
        done = list(row.delivered_to or [])
        error: str | None = None
        for sub_name, handler in subscribers(row.event).items():
            if sub_name in done:
                continue
            try:
                async with session.begin_nested():
                    await handler(session, event)
                done.append(sub_name)
            except Exception as exc:
                error = f"{sub_name}: {type(exc).__name__}"
                log.warning("outbox.subscriber_failed", event_id=str(row.id), subscriber=sub_name)
        row.delivered_to = done
        if error is None:
            row.delivered_at = now
            delivered += 1
        else:
            row.attempts += 1
            row.last_error = error
            row.next_attempt_at = now + _backoff(row.attempts)
    return delivered
