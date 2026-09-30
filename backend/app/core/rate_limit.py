"""Fixed-window rate limits backed by the cache adapter (Valkey)."""

from app.adapters.cache import get_cache
from app.core.errors import AppError


async def enforce(key: str, *, limit: int, window_seconds: int) -> None:
    count = await get_cache().incr_window(f"rl:{key}", window_seconds)
    if count > limit:
        raise AppError("RATE_LIMITED", 429, {"retry_after_s": window_seconds})
