from typing import Protocol


class Cache(Protocol):
    async def incr_window(self, key: str, window_seconds: int) -> int:
        """Increment a counter expiring `window_seconds` after its first hit; return the count."""
        ...

    async def ping(self) -> bool: ...
