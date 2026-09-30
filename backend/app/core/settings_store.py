"""Tunable values from the `settings` table, cached per process (spec section 4)."""

import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.core.errors import AppError
from app.core.models import Setting

_cache: dict[str, tuple[Any, float]] = {}


def clear_cache() -> None:
    _cache.clear()


async def get_setting(session: AsyncSession, key: str) -> Any:
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and hit[1] > now:
        return hit[0]
    value = await session.scalar(select(Setting.value).where(Setting.key == key))
    if value is None:
        raise AppError("SETTING_MISSING", 500, {"key": key})
    _cache[key] = (value, now + get_config().settings_cache_seconds)
    return value


async def get_int(session: AsyncSession, key: str) -> int:
    value = await get_setting(session, key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise AppError("SETTING_INVALID", 500, {"key": key})
    return value


async def list_settings(session: AsyncSession) -> list[Setting]:
    return list(await session.scalars(select(Setting).order_by(Setting.key)))


async def get_row(session: AsyncSession, key: str) -> Setting | None:
    return await session.get(Setting, key)
