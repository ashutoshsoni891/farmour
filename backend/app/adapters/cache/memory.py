"""In-process cache fake for tests and single-process dev."""

import time


class MemoryCache:
    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}

    async def incr_window(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        count, expires = self._counters.get(key, (0, now + window_seconds))
        if now >= expires:
            count, expires = 0, now + window_seconds
        count += 1
        self._counters[key] = (count, expires)
        return count

    async def ping(self) -> bool:
        return True
