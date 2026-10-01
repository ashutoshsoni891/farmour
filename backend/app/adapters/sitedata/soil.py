"""Soil texture, pH and organic carbon from ISRIC SoilGrids (about 250 m, 0-30 cm)."""

import asyncio
import logging
from typing import Any

import httpx

from app.adapters.sitedata.base import Fact, SiteContext

log = logging.getLogger(__name__)
URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]
WEIGHTS = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}  # layer thickness in cm
ATTRIBUTION = "ISRIC SoilGrids (CC BY 4.0), estimated from public data"


def texture_to_soil_type(clay: float, sand: float) -> str:
    """Map texture percentages to the app's soil_type values (spec section 5)."""
    if sand >= 70:
        return "sandy"
    if clay >= 40:
        return "clay"
    if clay >= 15 or sand >= 30:
        return "loam"
    return "mixed"


def parse(payload: dict[str, Any]) -> dict[str, float]:
    """Depth-weighted 0-30 cm means in clay %, sand %, silt %, pH and organic carbon g/kg."""
    out: dict[str, float] = {}
    scale = {"clay": 10, "sand": 10, "silt": 10, "phh2o": 10, "soc": 10}  # SoilGrids d_factor
    for layer in payload.get("properties", {}).get("layers", []):
        name = layer.get("name")
        total = weight = 0.0
        for depth in layer.get("depths", []):
            mean = (depth.get("values") or {}).get("mean")
            w = WEIGHTS.get(depth.get("label", ""))
            if mean is not None and w:
                total += mean * w
                weight += w
        if name in scale and weight:
            out[name] = round(total / weight / scale[name], 2)
    return out


class SoilGridsSource:
    name = "soilgrids"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def _query(
        self, ctx: SiteContext, props: tuple[str, ...], timeouts: tuple[float, ...]
    ) -> dict[str, float]:
        params: list[tuple[str, str | int | float | bool | None]] = [
            ("lon", f"{ctx.lng:.5f}"), ("lat", f"{ctx.lat:.5f}"),
        ]  # fmt: skip
        params += [("property", p) for p in props] + [("depth", d) for d in DEPTHS]
        params.append(("value", "mean"))
        for attempt, timeout in enumerate(timeouts):
            try:
                async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                    resp = await client.get(URL, params=params)
                    resp.raise_for_status()
                return parse(resp.json())
            except (httpx.HTTPError, ValueError) as exc:
                log.warning(
                    "soilgrids %s attempt %d failed: %s", props, attempt + 1, type(exc).__name__
                )
                await asyncio.sleep(1)
        return {}

    async def fetch(self, ctx: SiteContext) -> list[Fact]:
        # Response time grows with properties x depths, so texture (essential) and the extras
        # (pH, organic carbon) are separate requests made at the same time.
        core, extra = await asyncio.gather(
            self._query(ctx, ("clay", "sand", "silt"), (9, 5)),  # texture: retried once
            self._query(ctx, ("phh2o", "soc"), (6,)),  # pH / organic carbon: one quick try
        )
        v = core | extra
        if "clay" not in v or "sand" not in v:
            return []
        facts = [
            Fact("soil.type", texture_to_soil_type(v["clay"], v["sand"]), self.name,
                 "texture_class", 0.5, ttl_days=3650, attribution=ATTRIBUTION),
            Fact("soil.clay_pct", v["clay"], self.name, "depth_weighted_mean_0_30cm", 0.6, "%",
                 3650, ATTRIBUTION),
            Fact("soil.sand_pct", v["sand"], self.name, "depth_weighted_mean_0_30cm", 0.6, "%",
                 3650, ATTRIBUTION),
        ]  # fmt: skip
        if "silt" in v:
            facts.append(Fact("soil.silt_pct", v["silt"], self.name, "depth_weighted_mean_0_30cm",
                              0.6, "%", 3650, ATTRIBUTION))  # fmt: skip
        if "phh2o" in v:
            facts.append(Fact("soil.ph", v["phh2o"], self.name, "depth_weighted_mean_0_30cm",
                              0.6, "pH", 3650, ATTRIBUTION))  # fmt: skip
        if "soc" in v:
            facts.append(Fact("soil.organic_carbon_g_kg", v["soc"], self.name,
                              "depth_weighted_mean_0_30cm", 0.5, "g/kg", 3650, ATTRIBUTION))  # fmt: skip
        return facts
