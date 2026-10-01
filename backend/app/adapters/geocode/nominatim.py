"""Nominatim (OpenStreetMap) geocoder, following the public usage policy: an identifying
User-Agent, at most one request per second, results cached, no autocomplete.

For heavier use, point NOMINATIM_URL at a self-hosted Nominatim or Photon instance.
"""

import asyncio
import time
from typing import Any

import httpx

from app.adapters.geocode.base import Place

_CACHE_MAX = 500


class NominatimGeocoder:
    def __init__(self, base_url: str, user_agent: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"User-Agent": user_agent}
        self._lock = asyncio.Lock()
        self._last_call = 0.0
        self._cache: dict[tuple[Any, ...], Any] = {}

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        key = (path, tuple(sorted(params.items())))
        if key in self._cache:
            return self._cache[key]
        async with self._lock:  # serialises calls so the 1 request/second rule holds
            wait = 1.0 - (time.monotonic() - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with httpx.AsyncClient(timeout=8, headers=self._headers) as client:
                    resp = await client.get(f"{self._base}{path}", params=params)
                    resp.raise_for_status()
            finally:
                self._last_call = time.monotonic()
        data = resp.json()
        if len(self._cache) >= _CACHE_MAX:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = data
        return data

    @staticmethod
    def _place(item: dict[str, Any]) -> Place:
        addr = item.get("address") or {}
        village = next(
            (addr[k] for k in ("village", "hamlet", "suburb", "town", "city") if addr.get(k)), None
        )
        district = addr.get("state_district") or addr.get("county") or addr.get("city_district")
        return Place(
            name=str(item.get("display_name", ""))[:200],
            lat=float(item["lat"]),
            lng=float(item["lon"]),
            village=village,
            district=district,
            state=addr.get("state"),
        )

    async def search(self, query: str, *, lang: str, limit: int) -> list[Place]:
        data = await self._get(
            "/search",
            {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": limit,
             "countrycodes": "in", "accept-language": lang},
        )  # fmt: skip
        return [self._place(i) for i in data]

    async def reverse(self, lat: float, lng: float, *, lang: str) -> Place | None:
        data = await self._get(
            "/reverse",
            {"lat": round(lat, 4), "lon": round(lng, 4), "format": "jsonv2", "zoom": 14,
             "addressdetails": 1, "accept-language": lang},
        )  # fmt: skip
        return None if "error" in data else self._place(data)
