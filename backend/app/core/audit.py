"""Append-only audit trail (spec section 2): plans, library, money logs, settings, members."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditLog


async def record(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    entity: str,
    entity_id: str | uuid.UUID,
    action: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            before=before,
            after=after,
            reason=reason,
        )
    )
