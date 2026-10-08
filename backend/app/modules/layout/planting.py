"""Crop assignment (spec 7, step 8): which crop goes in which layer of which bed, per season.

Pure and deterministic. For each season in the plan (12 months from the start date), each bed in
code order and each layer (underground -> surface -> middle -> climber, climber only on trellis
beds), the candidates that pass every hard rule are scored and the best one is taken; ties go to
the crop slug. Every agronomy value comes from the crop library through `CropSpec`.
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

LAYERS = ("underground", "surface", "middle", "climber")
WATER_LEVEL = {"low": 0.0, "medium": 0.5, "high": 1.0}


@dataclass(frozen=True)
class CropSpec:
    slug: str
    status: str
    family: str | None
    layers: tuple[str, ...]
    seasons: tuple[str, ...]
    sow_windows: tuple[tuple[str, str, str], ...]  # (from MM-DD, to MM-DD, method)
    days_to_first_harvest: int | None
    harvest_span_days: int | None
    spacing_row_cm: int | None
    spacing_plant_cm: int | None
    height_max_cm: int | None
    water_need: str | None
    waterlogging_tolerant: bool | None
    yield_kg_per_sqm: float | None
    low_care: bool | None
    price_paise_per_kg: int | None
    category: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class BedSpec:
    code: str
    area_sqm: float
    length_m: float
    width_m: float
    raised: bool
    has_trellis: bool


@dataclass(frozen=True)
class PlantingParams:
    weights: dict[str, float]  # value, diversity, ease, water (rules: engine.score)
    goal_income_value: float
    goal_home_food_diversity: float
    repeat_diversity: float
    crowding: dict[str, float]  # per layer (rules: engine.crowding)
    min_crops: dict[str, int]  # per template (rules: engine.min_crops)
    seasons: dict[str, dict[str, str]]  # season -> {from, to} MM-DD (rules: engine.seasons)
    plan_days: int
    tall_crop_cm: int
    good_companion_bonus: float
    medicinal_bed_share: float = 0.0  # share of beds given to medicinal herbs when asked for


@dataclass(frozen=True)
class SeasonSlot:
    season: str
    label: str  # e.g. "rabi 2026-27"
    begin: date
    end: date


@dataclass
class Planting:
    bed: str
    slot: SeasonSlot
    layer: str
    crop: str
    planned_sow: date
    harvest_start: date
    harvest_end: date
    plant_count: int
    spacing_cm: int
    expected_yield_kg: float
    why: dict[str, Any]


@dataclass
class PlantingResult:
    slots: list[SeasonSlot]
    plantings: list[Planting]
    warnings: list[dict[str, Any]] = field(default_factory=list)
    uses_ai_verified: bool = False


def _md(year: int, mmdd: str) -> date:
    month, day = int(mmdd[:2]), int(mmdd[3:])
    if month == 2 and day == 29:
        day = 28  # keep Feb 29 windows valid in every year
    return date(year, month, day)


def _range(year: int, start: str, end: str) -> tuple[date, date]:
    """A MM-DD..MM-DD range starting in `year`; wraps into the next year when end < start."""
    begin = _md(year, start)
    finish = _md(year, end)
    if finish < begin:
        finish = _md(year + 1, end)
    return begin, finish


def season_slots(start: date, p: PlantingParams) -> list[SeasonSlot]:
    """Season occurrences that overlap the plan period, clipped to it, in date order."""
    horizon = start + timedelta(days=p.plan_days)
    slots = []
    for year in (start.year - 1, start.year, start.year + 1):
        for season, rng in p.seasons.items():
            begin, end = _range(year, rng["from"], rng["to"])
            begin, end = max(begin, start), min(end, horizon - timedelta(days=1))
            if begin > end:
                continue
            label = (
                f"{season} {year}"
                if begin.year == end.year
                else f"{season} {year}-{str(year + 1)[2:]}"
            )
            slots.append(SeasonSlot(season, label, begin, end))
    return sorted(slots, key=lambda s: s.begin)


def first_sow(crop: CropSpec, slot: SeasonSlot, not_before: date | None = None) -> date | None:
    """The first date inside the slot (and not before `not_before`) that falls in one of the
    crop's sow windows."""
    floor = max(slot.begin, not_before) if not_before else slot.begin
    best: date | None = None
    for year in (slot.begin.year - 1, slot.begin.year, slot.end.year):
        for start, end, _method in crop.sow_windows:
            begin, finish = _range(year, start, end)
            lo, hi = max(begin, floor), min(finish, slot.end)
            if lo <= hi and (best is None or lo < best):
                best = lo
    return best


def _done(crop: CropSpec, sow: date) -> date:
    """The day the layer is free again: first harvest plus the picking period."""
    return sow + timedelta(days=(crop.days_to_first_harvest or 0) + (crop.harvest_span_days or 0))


def _complete(crop: CropSpec) -> bool:
    return None not in (crop.spacing_plant_cm, crop.yield_kg_per_sqm, crop.days_to_first_harvest)


def assign(
    beds: list[BedSpec],
    crops: list[CropSpec],
    companions: list[tuple[str, str, str]],  # (slug, slug, "good" | "avoid")
    *,
    start: date,
    template: str,
    goal: str | None,
    drainage: str | None,
    p: PlantingParams,
    weights: dict[str, float] | None = None,
    allow_flowers: bool = False,
    allow_medicinal: bool = False,
) -> PlantingResult:
    """Fill every bed. `weights` (a plan option's score weights) replaces the goal shift."""
    pairs = _pairs(companions)
    if weights is None:
        weights = dict(p.weights)
        if goal == "income":
            weights["value"] = p.goal_income_value
        elif goal == "home_food":
            weights["diversity"] = p.goal_home_food_diversity
    else:
        weights = {**p.weights, **weights}
    by_slug = {c.slug: c for c in crops}
    # Flowers and medicinal herbs go in beds only when the owner asked for them (goal step).
    usable = [
        c for c in sorted(crops, key=lambda c: c.slug)
        if _complete(c)
        and (allow_flowers or c.category != "flower")
        and (allow_medicinal or "medicinal" not in c.tags)
    ]  # fmt: skip
    use_price = bool(usable) and all(c.price_paise_per_kg for c in usable)

    result = PlantingResult(slots=[], plantings=[])
    if not use_price:
        result.warnings.append({"code": "NO_PRICES", "message_key": "warn.no_prices"})
    previous: dict[str, set[str]] = {}  # bed -> families planted in the previous slot
    busy: dict[tuple[str, str], date] = {}  # (bed, layer) -> date the layer is free again
    med_beds = math.ceil(p.medicinal_bed_share * len(beds)) if allow_medicinal else 0
    for slot in season_slots(start, p):
        # Eligibility follows the crops' own sow windows (season names are only a calendar).
        if not any(first_sow(c, slot) for c in usable):
            continue
        result.slots.append(slot)
        used: dict[str, int] = {}
        layer_used: dict[tuple[str, str], int] = {}  # (layer, crop) -> beds this slot
        layer_total: dict[str, int] = {}
        current: dict[str, set[str]] = {}
        for bed_no, bed in enumerate(beds):
            medicinal_bed = bed_no < med_beds
            in_bed: list[str] = []
            for layer in LAYERS:
                if layer == "climber" and not bed.has_trellis:
                    continue
                free = busy.get((bed.code, layer))
                sow = {c.slug: first_sow(c, slot, free) for c in usable if layer in c.layers}
                candidates = [
                    by_slug[s] for s, d in sorted(sow.items())
                    if d is not None
                    and _allowed(by_slug[s], bed, in_bed, previous.get(bed.code, set()),
                                 drainage, pairs, p)
                ]  # fmt: skip
                # The first beds are the herbs' (when asked for); the rest keep to food crops.
                herbs = [c for c in candidates if "medicinal" in c.tags]
                if medicinal_bed and herbs:
                    candidates = herbs
                elif not medicinal_bed:
                    candidates = [c for c in candidates if "medicinal" not in c.tags]
                if not candidates:
                    continue
                values = {c.slug: _value(c, use_price) for c in candidates}
                if medicinal_bed and herbs:
                    # kg of fresh leaf and kg of dried root are not comparable: with no prices to
                    # compare, herbs are ranked on diversity, ease and water only
                    values = {c.slug: 1.0 for c in candidates}
                top = max(values.values()) or 1.0
                total = layer_total.get(layer, 0)
                scores = {
                    c.slug: _score(
                        c, values[c.slug] / top,
                        layer_used.get((layer, c.slug), 0) / total if total else 0.0,
                        used.get(c.slug, 0) == 0, in_bed, pairs, weights, p,
                    )
                    for c in candidates
                }  # fmt: skip
                best = max(candidates, key=lambda c: (round(scores[c.slug], 9), _neg(c.slug)))
                sown = sow[best.slug]
                if sown is None:  # cannot happen: candidates all have a sow date
                    continue
                partner = next(
                    (o for o in in_bed if pairs.get(frozenset((best.slug, o))) == "good"), None
                )
                if partner:
                    why: dict[str, Any] = {"key": "plan.why.companion", "partner": partner}
                elif used.get(best.slug, 0) == 0:
                    why = {"key": "plan.why.variety"}
                elif values[best.slug] == top:
                    why = {"key": "plan.why.yield"}
                else:
                    why = {"key": "plan.why.fits"}
                result.plantings.append(_planting(bed, slot, layer, best, sown, why, p))
                busy[(bed.code, layer)] = _done(best, sown)
                in_bed.append(best.slug)
                used[best.slug] = used.get(best.slug, 0) + 1
                layer_used[(layer, best.slug)] = layer_used.get((layer, best.slug), 0) + 1
                layer_total[layer] = total + 1
                if best.status == "ai_verified":
                    result.uses_ai_verified = True
            current[bed.code] = {by_slug[s].family or s for s in in_bed}
        previous = current
        distinct = len(used)
        if distinct < p.min_crops.get(template, 0):
            result.warnings.append(
                {"code": "FEW_CROPS", "message_key": "warn.few_crops",
                 "params": {"season": slot.label, "n": distinct, "min": p.min_crops[template]}}
            )  # fmt: skip
    if not result.plantings:
        result.warnings.append({"code": "NO_CROPS", "message_key": "warn.no_crops"})
    return result


def _pairs(companions: list[tuple[str, str, str]]) -> dict[frozenset[str], str]:
    return {frozenset((a, b)): rel for a, b, rel in companions if a != b}


def _allowed(
    c: CropSpec,
    bed: BedSpec,
    in_bed: list[str],
    previous_families: set[str],
    drainage: str | None,
    pairs: dict[frozenset[str], str],
    p: PlantingParams,
) -> bool:
    """Spec 7 hard rules for one crop in one bed (layer and sow date are checked by the caller)."""
    return (
        c.slug not in in_bed
        and (c.height_max_cm or 0) <= p.tall_crop_cm
        and not (drainage == "waterlogs" and not bed.raised and not c.waterlogging_tolerant)
        and (c.family or c.slug) not in previous_families
        and not any(pairs.get(frozenset((c.slug, o))) == "avoid" for o in in_bed)
    )


def _planting(
    bed: BedSpec,
    slot: SeasonSlot,
    layer: str,
    crop: CropSpec,
    sown: date,
    why: dict[str, Any],
    p: PlantingParams,
) -> Planting:
    rows = max(1, int(bed.width_m * 100 // crop.spacing_row_cm)) if crop.spacing_row_cm else 1
    per_row = max(1, int(bed.length_m * 100 // (crop.spacing_plant_cm or 1)))
    return Planting(
        bed=bed.code, slot=slot, layer=layer, crop=crop.slug, planned_sow=sown,
        harvest_start=sown + timedelta(days=crop.days_to_first_harvest or 0),
        harvest_end=_done(crop, sown), plant_count=rows * per_row,
        spacing_cm=crop.spacing_plant_cm or 0,
        expected_yield_kg=round(
            bed.area_sqm * (crop.yield_kg_per_sqm or 0) * p.crowding.get(layer, 1.0), 2
        ),
        why=why,
    )  # fmt: skip


def alternatives(
    bed: BedSpec,
    layer: str,
    slot: SeasonSlot,
    crops: list[CropSpec],
    companions: list[tuple[str, str, str]],
    *,
    others_in_bed: list[str],
    previous_families: set[str],
    free_from: date | None,
    must_end_by: date | None,
    drainage: str | None,
    p: PlantingParams,
) -> list[Planting]:
    """Every crop that could go in this bed layer in this season instead of the planned one:
    same hard rules as the engine, a sow date after the layer is free, and a harvest that ends
    before the next crop in that layer goes in."""
    if layer == "climber" and not bed.has_trellis:
        return []
    pairs = _pairs(companions)
    out = []
    for c in sorted(crops, key=lambda c: c.slug):
        if not _complete(c) or layer not in c.layers:
            continue
        if not _allowed(c, bed, others_in_bed, previous_families, drainage, pairs, p):
            continue
        sown = first_sow(c, slot, free_from)
        if sown is None or (must_end_by is not None and _done(c, sown) > must_end_by):
            continue
        out.append(_planting(bed, slot, layer, c, sown, {"key": "plan.why.owner"}, p))
    return out


def _value(c: CropSpec, use_price: bool) -> float:
    """Expected yield per sqm, times the local price when every candidate has one."""
    price = (c.price_paise_per_kg or 0) if use_price else 1
    return (c.yield_kg_per_sqm or 0) * price


def _score(
    c: CropSpec,
    value: float,
    layer_share: float,
    first_use: bool,
    in_bed: list[str],
    pairs: dict[frozenset[str], str],
    weights: dict[str, float],
    p: PlantingParams,
) -> float:
    """Spec 7 score: value + diversity + ease - water (+ a bonus next to a good companion).

    Diversity is 1 for a crop not yet used this season (spec); after that it falls with the share
    of this layer's beds the crop already has, so one high-yield crop cannot fill every bed
    (decision 2026-10-06; the spec's flat 0.3 let one crop take nearly all beds)."""
    diversity = 1.0 if first_use else (1.0 - layer_share)
    ease = 1.0 if c.low_care else 0.5
    water = WATER_LEVEL.get(c.water_need or "medium", 0.5)
    good = any(pairs.get(frozenset((c.slug, o))) == "good" for o in in_bed)
    return (
        weights["value"] * value
        + weights["diversity"] * diversity
        + weights["ease"] * ease
        + weights["water"] * water  # the water weight is negative (a penalty)
        + (p.good_companion_bonus if good else 0.0)
    )


def _neg(slug: str) -> tuple[int, ...]:
    """Sort key that makes max() prefer the alphabetically first slug on equal scores."""
    return (*(-ord(ch) for ch in slug), 0)
