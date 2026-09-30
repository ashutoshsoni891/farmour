"""Key-value cache and counters (Valkey in production)."""

from app.adapters.cache.base import Cache
from app.adapters.cache.memory import MemoryCache
from app.adapters.registry import Registry
from app.config import get_config

registry: Registry[Cache] = Registry("cache")
registry.register("memory", MemoryCache)


def _valkey() -> Cache:
    from app.adapters.cache.valkey import ValkeyCache

    return ValkeyCache(get_config().valkey_url)


registry.register("valkey", _valkey)


def get_cache() -> Cache:
    return registry.get(get_config().cache_adapter)


__all__ = ["Cache", "get_cache", "registry"]
