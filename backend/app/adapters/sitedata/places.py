"""Nearby input shops, nurseries and markets from OpenStreetMap via the Overpass API.

OSM coverage in rural India is patchy, so these are labelled low confidence and curated places
(KVKs, FPOs) take priority when they exist (spec section 17)."""

import logging
from typing import Any

import httpx

from app.adapters.routing import haversine_km
from app.adapters.sitedata.base import Fact, SiteContext
from app.config import get_config

log = logging.getLogger(__name__)
SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
RADIUS_M = 25_000
KINDS = {
    "input_shop": '["shop"="agrarian"]',
    "nursery": '["shop"="garden_centre"]',
    "cold_storage": '["industrial"="cold_storage"]',
}
ATTRIBUTION = "© OpenStreetMap contributors (ODbL)"
PER_KIND = 3


class OverpassPlacesSource:
    name = "osm_places"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(self, ctx: SiteContext) -> list[Fact]:
        around = f"(around:{RADIUS_M},{ctx.lat:.5f},{ctx.lng:.5f})"
        parts = "".join(f"nwr{tags}{around};" for tags in KINDS.values())
        query = f"[out:json][timeout:15];({parts});out center tags 60;"
        headers = {
            "User-Agent": get_config().geocoder_user_agent
        }  # Overpass asks clients to identify
        elements: list[dict[str, Any]] = []
        for url in SERVERS:
            try:
                async with httpx.AsyncClient(
                    timeout=15, transport=self._transport, headers=headers
                ) as client:
                    resp = await client.post(url, data={"data": query})
                    resp.raise_for_status()
                elements = resp.json().get("elements", [])
                break
            except (httpx.HTTPError, ValueError) as exc:
                log.warning("overpass %s unavailable: %s", url, type(exc).__name__)
        if not elements:
            return []
        found: dict[str, list[dict[str, Any]]] = {k: [] for k in KINDS}
        for el in elements:
            tags = el.get("tags") or {}
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lng = el.get("lon") or (el.get("center") or {}).get("lon")
            name = tags.get("name") or tags.get("name:en")
            if lat is None or lng is None or not name:
                continue
            kind = next((k for k, t in KINDS.items() if _matches(tags, t)), None)
            if kind:
                found[kind].append(
                    {
                        "name": name, "lat": lat, "lng": lng,
                        "distance_km": round(haversine_km((ctx.lat, ctx.lng), (lat, lng)), 1),
                        "phone": tags.get("phone") or tags.get("contact:phone"),
                    }
                )  # fmt: skip
        places = {
            k: sorted(v, key=lambda p: p["distance_km"])[:PER_KIND] for k, v in found.items() if v
        }
        if not places:
            return []
        return [Fact("nearby.places", places, self.name, "osm_within_25km", 0.3, None, 30, ATTRIBUTION)]  # fmt: skip


def _matches(tags: dict[str, Any], expr: str) -> bool:
    key, value = expr.strip('[]"').split('"="')
    return tags.get(key) == value
