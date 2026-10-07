"""Trees in the orchard strip and hedge plants along the border (spec 7: orchard/canopy and border
zones; vision: horticulture). Pure and deterministic; every number comes from the crop library or
the plan option's weights.

Trees go in east-west rows across the north strip, widest-spaced species furthest north so they
do not shade the rest; each row holds one species at its own spacing. Hedge plants are spaced
along the middle of the border band, leaving the gate open.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

from app.modules.layout.planting import WATER_LEVEL, CropSpec, SeasonSlot, first_sow


@dataclass(frozen=True)
class PerennialSpec:
    crop: CropSpec
    spacing_m: float  # tree spacing, or hedge spacing along the line
    years_to_bear: float | None
    first_harvest_days: int | None  # for hedge plants (e.g. curry leaf)


@dataclass
class PlacedPlant:
    crop: str
    kind: str  # "tree" or "hedge"
    point: Point  # local metres
    zone_index: int
    plant_on: date
    first_harvest: date | None
    spacing_m: float


def _plant_date(crop: CropSpec, start: date, plan_days: int) -> date:
    """First planting-window date in the plan period; the plan start if the source gives none."""
    if not crop.sow_windows:
        return start
    whole = SeasonSlot("perennial", "plan", start, start + timedelta(days=plan_days - 1))
    return first_sow(crop, whole) or start


def _tree_score(t: PerennialSpec, top_yield: float, weights: dict[str, float]) -> float:
    value = (t.crop.yield_kg_per_sqm or 0) / top_yield if top_yield else 0.0
    speed = 1 - min(t.years_to_bear or 10, 10) / 10  # sooner fruit is easier to live with
    water = WATER_LEVEL.get(t.crop.water_need or "medium", 0.5)
    return (
        weights.get("value", 0.4) * value
        + weights.get("ease", 0.2) * speed
        + weights.get("water", -0.1) * water
    )


def plant_orchard(
    zones: list[tuple[int, Polygon]],
    trees: list[PerennialSpec],
    *,
    weights: dict[str, float],
    start: date,
    plan_days: int,
    max_species: int,
    max_short_lived: int = 1,
    short_lived_max_years: float = 1.0,
) -> list[PlacedPlant]:
    """Fill each orchard zone with rows of trees. At most `max_short_lived` of the chosen species
    may fruit within `short_lived_max_years` (they out-yield long-lived trees per m2)."""
    if not trees:
        return []
    top = max((t.crop.yield_kg_per_sqm or 0) for t in trees) or 1.0
    ranked = sorted(trees, key=lambda t: (-round(_tree_score(t, top, weights), 9), t.crop.slug))
    chosen: list[PerennialSpec] = []
    short = 0
    for t in ranked:
        if len(chosen) >= max(1, max_species):
            break
        quick = t.years_to_bear is not None and t.years_to_bear <= short_lived_max_years
        if quick and short >= max_short_lived:
            continue
        chosen.append(t)
        short += quick
    chosen = chosen or ranked[:1]
    placed: list[PlacedPlant] = []
    for zone_index, zone in zones:
        minx, miny, maxx, maxy = zone.bounds
        y = maxy
        # widest spacing to the north, then cycle
        order = sorted(chosen, key=lambda t: (-t.spacing_m, t.crop.slug))
        i = 0
        while y - miny > 0.5:
            fitting = [t for t in order if t.spacing_m <= (y - miny) + 1e-6]
            if not fitting:
                break
            t = next((x for x in order[i % len(order) :] + order if x in fitting), fitting[0])
            i += 1
            cy = y - t.spacing_m / 2
            x = minx + t.spacing_m / 2
            row = 0
            while x < maxx:
                pt = Point(x, cy)
                if zone.contains(pt) and zone.exterior.distance(pt) >= t.spacing_m * 0.3:
                    plant_on = _plant_date(t.crop, start, plan_days)
                    first = (
                        plant_on + timedelta(days=round((t.years_to_bear or 0) * 365))
                        if t.years_to_bear is not None else None
                    )  # fmt: skip
                    placed.append(PlacedPlant(t.crop.slug, "tree", pt, zone_index, plant_on, first,
                                              t.spacing_m))  # fmt: skip
                    row += 1
                x += t.spacing_m
            y -= t.spacing_m
    return placed


def plant_hedge(
    line: BaseGeometry | None,
    zone_index: int,
    hedges: list[PerennialSpec],
    *,
    weights: dict[str, float],
    gate: Point | None,
    gate_gap_m: float,
    start: date,
    plan_days: int,
) -> list[PlacedPlant]:
    """Space the best-scoring hedge plant along the border, leaving the gate open."""
    if line is None or not hedges or line.length <= 0:
        return []
    top = max((h.crop.yield_kg_per_sqm or 0) for h in hedges) or 1.0
    best = sorted(hedges, key=lambda h: (-round(_tree_score(h, top, weights), 9), h.crop.slug))[0]
    plant_on = _plant_date(best.crop, start, plan_days)
    first = (
        plant_on + timedelta(days=best.first_harvest_days)
        if best.first_harvest_days is not None else None
    )  # fmt: skip
    out = []
    d = best.spacing_m / 2
    while d < line.length:
        pt = line.interpolate(d)
        if gate is None or pt.distance(gate) > gate_gap_m / 2 + best.spacing_m / 2:
            out.append(PlacedPlant(best.crop.slug, "hedge", pt, zone_index, plant_on, first,
                                   best.spacing_m))  # fmt: skip
        d += best.spacing_m
    return out
