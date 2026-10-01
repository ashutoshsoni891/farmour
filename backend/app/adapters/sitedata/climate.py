"""Climate normals and terrain from Open-Meteo (free API, non-commercial use; see decisions)."""

import logging
import math
from collections import defaultdict
from datetime import date
from typing import Any

import httpx

from app.adapters.sitedata.base import Fact, SiteContext

log = logging.getLogger(__name__)
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
ELEVATION = "https://api.open-meteo.com/v1/elevation"
ATTRIBUTION = "Open-Meteo.com (CC BY 4.0), ERA5 reanalysis"
YEARS = 10
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def monthly_normals(daily: dict[str, list[Any]]) -> dict[str, list[float]] | None:
    """Monthly mean of daily max/min temperature and mean monthly rainfall total."""
    t_max: dict[int, list[float]] = defaultdict(list)
    t_min: dict[int, list[float]] = defaultdict(list)
    rain: dict[tuple[int, int], float] = defaultdict(float)
    years: set[int] = set()
    for day, hi, lo, mm in zip(
        daily.get("time", []),
        daily.get("temperature_2m_max", []),
        daily.get("temperature_2m_min", []),
        daily.get("precipitation_sum", []),
        strict=False,
    ):
        y, m = int(day[:4]), int(day[5:7])
        years.add(y)
        if hi is not None:
            t_max[m].append(hi)
        if lo is not None:
            t_min[m].append(lo)
        if mm is not None:
            rain[(y, m)] += mm
    if len(years) < 3 or len(t_max) < 12:
        return None
    return {
        "tmax": [round(sum(t_max[m]) / len(t_max[m]), 1) for m in range(1, 13)],
        "tmin": [round(sum(t_min[m]) / len(t_min[m]), 1) for m in range(1, 13)],
        "rain": [
            round(sum(rain.get((y, m), 0.0) for y in years) / len(years), 1) for m in range(1, 13)
        ],
    }


def monsoon_onset_month(rain_mm: list[float], threshold_mm: float = 100.0) -> str | None:
    """First month from May on whose mean rainfall reaches the threshold."""
    for m in range(4, 12):
        if rain_mm[m] >= threshold_mm:
            return MONTHS[m]
    return None


def slope_from_grid(
    centre: float, north: float, south: float, east: float, west: float, step_m: float
) -> dict[str, Any]:
    """Gradient and downhill side from five elevation samples `step_m` apart."""
    dz_dy = (north - south) / (2 * step_m)  # rises toward north when positive
    dz_dx = (east - west) / (2 * step_m)
    gradient = math.hypot(dz_dx, dz_dy)
    pct = round(gradient * 100, 1)
    if gradient == 0:
        return {"gradient_pct": 0.0, "lower_side": None}
    downhill = math.degrees(math.atan2(-dz_dx, -dz_dy)) % 360  # bearing of steepest descent
    sides = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return {"gradient_pct": pct, "lower_side": sides[int((downhill + 22.5) // 45) % 8]}


class OpenMeteoClimateSource:
    name = "open_meteo"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(self, ctx: SiteContext) -> list[Fact]:
        end = date.today().replace(month=1, day=1)  # complete calendar years only
        start = end.replace(year=end.year - YEARS)
        params = {
            "latitude": f"{ctx.lat:.4f}", "longitude": f"{ctx.lng:.4f}",
            "start_date": start.isoformat(), "end_date": (end - date.resolution).isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "Asia/Kolkata",
        }  # fmt: skip
        try:
            async with httpx.AsyncClient(timeout=20, transport=self._transport) as client:
                resp = await client.get(ARCHIVE, params=params)
                resp.raise_for_status()
            normals = monthly_normals(resp.json().get("daily", {}))
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("open-meteo climate unavailable: %s", type(exc).__name__)
            return []
        if normals is None:
            return []
        annual = round(sum(normals["rain"]), 0)
        # Sanity range for Madhya Pradesh (spec 17): implausible values get low confidence.
        conf = 0.8 if 100 <= annual <= 5000 else 0.2
        hot = max(range(12), key=lambda i: normals["tmax"][i])
        cold = min(range(12), key=lambda i: normals["tmin"][i])
        meta: dict[str, Any] = {"unit": None, "ttl_days": 365, "attribution": ATTRIBUTION}
        facts = [
            Fact("climate.rain_monthly_mm", normals["rain"], self.name, f"{YEARS}y_mean", conf, "mm", 365, ATTRIBUTION),
            Fact("climate.tmax_monthly_c", normals["tmax"], self.name, f"{YEARS}y_mean", conf, "°C", 365, ATTRIBUTION),
            Fact("climate.tmin_monthly_c", normals["tmin"], self.name, f"{YEARS}y_mean", conf, "°C", 365, ATTRIBUTION),
            Fact("climate.annual_rain_mm", annual, self.name, f"{YEARS}y_mean", conf, "mm", 365, ATTRIBUTION),
            Fact("climate.hottest_month", {"month": MONTHS[hot], "tmax_c": normals["tmax"][hot]}, self.name, f"{YEARS}y_mean", conf, None, 365, ATTRIBUTION),
            Fact("climate.coldest_month", {"month": MONTHS[cold], "tmin_c": normals["tmin"][cold]}, self.name, f"{YEARS}y_mean", conf, None, 365, ATTRIBUTION),
        ]  # fmt: skip
        onset = monsoon_onset_month(normals["rain"])
        if onset:
            facts.append(Fact("climate.monsoon_onset", onset, self.name, "first_month_100mm", conf * 0.8, None, 365, ATTRIBUTION))  # fmt: skip
        del meta
        return facts


class OpenMeteoTerrainSource:
    """Elevation and slope from five samples ~90 m apart (the DEM grid size).

    Plots smaller than the grid get an elevation but only low-confidence slope."""

    name = "open_meteo_dem"
    STEP_M = 90.0

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def fetch(self, ctx: SiteContext) -> list[Fact]:
        dlat = self.STEP_M / 111_320
        dlng = self.STEP_M / (111_320 * math.cos(math.radians(ctx.lat)))
        pts = [
            (ctx.lat, ctx.lng), (ctx.lat + dlat, ctx.lng), (ctx.lat - dlat, ctx.lng),
            (ctx.lat, ctx.lng + dlng), (ctx.lat, ctx.lng - dlng),
        ]  # fmt: skip
        params = {
            "latitude": ",".join(f"{p[0]:.5f}" for p in pts),
            "longitude": ",".join(f"{p[1]:.5f}" for p in pts),
        }
        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                resp = await client.get(ELEVATION, params=params)
                resp.raise_for_status()
            e = [float(x) for x in resp.json()["elevation"]]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            log.warning("open-meteo elevation unavailable: %s", type(exc).__name__)
            return []
        if len(e) != 5:
            return []
        slope = slope_from_grid(e[0], e[1], e[2], e[3], e[4], self.STEP_M)
        small = ctx.area_sqm is not None and ctx.area_sqm < self.STEP_M * self.STEP_M / 4
        conf = 0.3 if small else 0.5  # a small plot is smaller than the ~90 m DEM cell
        facts = [Fact("terrain.elevation_m", round(e[0]), self.name, "dem_90m", 0.7, "m", 3650, ATTRIBUTION)]  # fmt: skip
        facts.append(Fact("terrain.slope", slope, self.name, "five_point_gradient", conf, None, 3650, ATTRIBUTION))  # fmt: skip
        return facts
