"""Valkey implementation. Valkey speaks the Redis protocol; uses the BSD-licensed redis-py."""

import redis.asyncio as redis


class ValkeyCache:
    def __init__(self, url: str) -> None:
        self._client = redis.from_url(url)

    async def incr_window(self, key: str, window_seconds: int) -> int:
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = await pipe.execute()
        return int(count)

    async def ping(self) -> bool:
        return bool(await self._client.ping())
