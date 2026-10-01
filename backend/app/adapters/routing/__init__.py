"""Road distance and drive time (self-hosted OSRM on OpenStreetMap data)."""

import math
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.adapters.registry import Registry
from app.config import get_config


@dataclass(frozen=True)
class RouteResult:
    distance_km: float
    minutes: float
    method: str  # "osrm" or "straight_line"


class Router(Protocol):
    async def route(
        self, origin: tuple[float, float], dest: tuple[float, float]
    ) -> RouteResult | None:
        """origin/dest are (lat, lng). None when no route is known."""
        ...


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi, dlmb = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class OsrmRouter:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._base = base_url.rstrip("/")
        self._transport = transport

    async def route(
        self, origin: tuple[float, float], dest: tuple[float, float]
    ) -> RouteResult | None:
        url = f"{self._base}/route/v1/driving/{origin[1]:.5f},{origin[0]:.5f};{dest[1]:.5f},{dest[0]:.5f}"
        try:
            async with httpx.AsyncClient(timeout=6, transport=self._transport) as client:
                resp = await client.get(url, params={"overview": "false"})
                resp.raise_for_status()
            route = resp.json()["routes"][0]
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None
        return RouteResult(
            round(route["distance"] / 1000, 1), round(route["duration"] / 60), "osrm"
        )


class FakeRouter:
    """Deterministic: 1.3 x the straight-line distance at 40 km/h."""

    async def route(
        self, origin: tuple[float, float], dest: tuple[float, float]
    ) -> RouteResult | None:
        km = round(haversine_km(origin, dest) * 1.3, 1)
        return RouteResult(km, round(km / 40 * 60), "fake")


registry: Registry[Router] = Registry("routing")
registry.register("fake", FakeRouter)


def _osrm() -> Router:
    return OsrmRouter(get_config().osrm_url)


registry.register("osrm", _osrm)


def get_router() -> Router:
    return registry.get(get_config().routing_adapter)
