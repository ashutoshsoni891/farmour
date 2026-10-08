"""Field crops on the rotation field (spec 7, step 8 for the plots that are not beds).

Pure and deterministic, like `planting`: the rotation zone is cut into plots, and each season every
plot takes one crop that passes the hard rules (sowing window, a different family from the last crop
on that plot, waterlogging) with the best score; a green manure goes in when nothing fits. Every
agronomy value comes from the crop library through `CropSpec`.
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from shapely.geometry import Polygon, box
from shapely.geometry.base import BaseGeometry

from app.modules.layout import planting
from app.modules.layout.planting import CropSpec, PlantingParams, SeasonSlot

# Crops that go in beds, orchard strip, border or flower beds are not field crops; neither are
# perennials (they would block a plot for years).
NOT_FIELD = {"fruit_tree", "fruit_short", "border", "flower", "green_manure"}


@dataclass(frozen=True)
class FieldPlot:
    code: str
    geom: Polygon  # projected (metres)
    area_sqm: float


@dataclass(frozen=True)
class FieldPlanting:
    plot: str
    slot: SeasonSlot
    crop: str
    planned_sow: date
    harvest_start: date
    harvest_end: date
    area_sqm: float
    plant_count: int | None
    expected_yield_kg: float
    why: dict[str, Any]


@dataclass
class FieldResult:
    plantings: list[FieldPlanting] = field(default_factory=list)
    uses_ai_verified: bool = False
    warnings: list[dict[str, Any]] = field(default_factory=list)


def is_field_crop(c: CropSpec) -> bool:
    return (
        not c.layers
        and c.category not in NOT_FIELD
        and "perennial" not in c.seasons
        and None not in (c.days_to_first_harvest, c.spacing_row_cm, c.yield_kg_per_sqm)
    )


def is_green_manure(c: CropSpec) -> bool:
    return (
        c.category == "green_manure"
        and "perennial" not in c.seasons
        and None not in (c.days_to_first_harvest, c.spacing_row_cm)
    )


def split_plots(zone: BaseGeometry, count: int, min_plot_sqm: float) -> list[FieldPlot]:
    """Cut a rotation zone into up to `count` plots of equal area across its longer side. A zone
    too small for plots of `min_plot_sqm` stays whole."""
    if zone.is_empty:
        return []
    n = max(1, min(count, int(zone.area // max(min_plot_sqm, 1.0))))
    minx, miny, maxx, maxy = zone.bounds
    along_x = (maxx - minx) >= (maxy - miny)
    lo, hi = (minx, maxx) if along_x else (miny, maxy)

    def part(a: float, b: float) -> BaseGeometry:
        return zone.intersection(box(a, miny, b, maxy) if along_x else box(minx, a, maxx, b))

    cuts = [lo]
    for k in range(1, n):
        target, a, b = zone.area * k / n, lo, hi
        for _ in range(40):  # bisection on the cut line until the area to its left matches
            mid = (a + b) / 2
            if part(lo, mid).area < target:
                a = mid
            else:
                b = mid
        cuts.append((a + b) / 2)
    cuts.append(hi)
    plots: list[FieldPlot] = []
    for i in range(n):
        piece = part(cuts[i], cuts[i + 1])
        polys = [g for g in getattr(piece, "geoms", [piece]) if isinstance(g, Polygon)]
        if polys:
            biggest = max(polys, key=lambda g: g.area)
            plots.append(FieldPlot(f"F{len(plots) + 1}", biggest, biggest.area))
    return plots


def _first_open(herbs: list[CropSpec], slot: SeasonSlot) -> date | None:
    """The first day in a season that any of these crops can be sown."""
    days = [d for c in herbs if (d := planting.first_sow(c, slot, None)) is not None]
    return min(days, default=None)


def _past(c: CropSpec, sown: date, limit: date | None) -> bool:
    """Is the crop still on the plot after `limit`?"""
    return limit is not None and planting._done(c, sown) > limit


def assign_fields(
    plots: list[FieldPlot],
    crops: list[CropSpec],
    *,
    start: date,
    drainage: str | None,
    p: PlantingParams,
    weights: dict[str, float],
    allow_medicinal: bool = False,
) -> FieldResult:
    """One crop per plot per season, in plot order."""
    result = FieldResult()
    if not plots:
        return result
    usable = [
        c for c in sorted(crops, key=lambda c: c.slug)
        if is_field_crop(c) and (allow_medicinal or "medicinal" not in c.tags)
    ]  # fmt: skip
    manures = [c for c in sorted(crops, key=lambda c: c.slug) if is_green_manure(c)]
    use_price = bool(usable) and all(c.price_paise_per_kg for c in usable)
    herb_plots = math.ceil(p.medicinal_bed_share * len(plots)) if allow_medicinal else 0
    last_family: dict[str, str] = {}  # plot -> family of its last crop
    last_crop: dict[str, str] = {}
    free: dict[str, date] = {}  # plot -> day it is free again
    slots = planting.season_slots(start, p)
    herbs_all = [c for c in usable if "medicinal" in c.tags]
    # the day each season's first herb can go in: a herb plot keeps clear for it
    herb_open = [_first_open(herbs_all, sl) for sl in slots]
    for i, slot in enumerate(slots):
        used: dict[str, int] = {}
        for no, plot in enumerate(plots):
            herb_plot = no < herb_plots
            floor = free.get(plot.code)
            sow = {c.slug: planting.first_sow(c, slot, floor) for c in usable}
            candidates = [
                c for c in usable
                if sow[c.slug] is not None
                and (c.family or c.slug) != last_family.get(plot.code)
                and not (drainage == "waterlogs" and not c.waterlogging_tolerant)
            ]  # fmt: skip
            # a crop of this season, and one the other plots have not taken, when there is one
            in_season = [c for c in candidates if slot.season in c.seasons]
            candidates = in_season or candidates
            fresh = [c for c in candidates if used.get(c.slug, 0) == 0]
            candidates = fresh or candidates
            herbs = [c for c in candidates if "medicinal" in c.tags]
            keep_clear = min((d for d in herb_open[i + 1 :] if d is not None), default=None)
            if herb_plot and not herbs and keep_clear is not None:
                # no herb fits now but one will: only a crop that is off the plot by then
                candidates = [
                    c for c in candidates if not _past(c, sow[c.slug] or start, keep_clear)
                ]
            if herb_plot and herbs:
                candidates = herbs
            elif not herb_plot:
                candidates = [c for c in candidates if "medicinal" not in c.tags]
            if candidates:
                values = {c.slug: planting._value(c, use_price) for c in candidates}
                if herb_plot and herbs:
                    values = {
                        c.slug: 1.0 for c in candidates
                    }  # kg of different herbs don't compare
                top = max(values.values()) or 1.0
                scores = {
                    c.slug: planting._score(
                        c, values[c.slug] / top,
                        used.get(c.slug, 0) / len(plots), used.get(c.slug, 0) == 0,
                        [], {}, weights, p,
                    )
                    for c in candidates
                }  # fmt: skip
                best = max(
                    candidates, key=lambda c: (round(scores[c.slug], 9), planting._neg(c.slug))
                )
                if herb_plot and "medicinal" in best.tags:
                    why: dict[str, Any] = {"key": "plan.why.medicinal"}
                elif plot.code in last_crop:
                    why = {"key": "plan.why.rotation"}
                elif used.get(best.slug, 0) == 0:
                    why = {"key": "plan.why.variety"}
                else:
                    why = {"key": "plan.why.fits"}
            else:
                manure_sow = {c.slug: planting.first_sow(c, slot, floor) for c in manures}
                fit = [
                    c for c in manures
                    if (sown_on := manure_sow[c.slug]) is not None
                    and (c.family or c.slug) != last_family.get(plot.code)
                    and not (herb_plot and _past(c, sown_on, keep_clear))
                ]  # fmt: skip
                if not fit:
                    continue
                best, sow = fit[0], manure_sow
                why = {"key": "plan.why.green_manure"}
            sown = sow[best.slug]
            if sown is None:
                continue
            ends = sown + timedelta(days=best.days_to_first_harvest or 0)
            row_cm, plant_cm = best.spacing_row_cm or 0, best.spacing_plant_cm
            result.plantings.append(
                FieldPlanting(
                    plot=plot.code, slot=slot, crop=best.slug, planned_sow=sown,
                    harvest_start=ends, harvest_end=planting._done(best, sown),
                    area_sqm=round(plot.area_sqm, 2),
                    plant_count=(
                        int(plot.area_sqm * 10000 // (row_cm * plant_cm))
                        if row_cm and plant_cm else None
                    ),
                    expected_yield_kg=round(plot.area_sqm * (best.yield_kg_per_sqm or 0), 2),
                    why=why,
                )
            )  # fmt: skip
            used[best.slug] = used.get(best.slug, 0) + 1
            last_family[plot.code] = best.family or best.slug
            last_crop[plot.code] = best.slug
            free[plot.code] = planting._done(best, sown)
            if best.status == "ai_verified":
                result.uses_ai_verified = True
    if not result.plantings:
        result.warnings.append({"code": "NO_FIELD_CROPS", "message_key": "warn.no_field_crops"})
    return result
