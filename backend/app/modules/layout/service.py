"""Layout module public entry point: build and read a farm's plan (spec section 7)."""

import asyncio
import dataclasses
import uuid
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from geoalchemy2.shape import to_shape
from pyproj import Geod
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, not_found
from app.core.settings_store import get_setting
from app.modules.farms import service as farms_service
from app.modules.farms.schemas import FarmOut
from app.modules.farms.service import Membership
from app.modules.layout import engine, perennials, planting
from app.modules.layout import repository as repo
from app.modules.layout.models import Plan
from app.modules.layout.schemas import (
    AdjustIn,
    AlternativeOut,
    BedOut,
    CropRef,
    Level,
    OptionMetrics,
    OptionOut,
    OptionsOut,
    PerennialOut,
    PlanOut,
    PlantingOut,
    PlanWarning,
    SeasonOut,
    SwapIn,
    ZoneOut,
)
from app.modules.library import service as library
from app.modules.library.schemas import EngineCrop
from app.modules.parcel import service as parcel_service
from app.modules.site import service as site_service
from app.modules.site.schemas import SchemeOut

IST = ZoneInfo("Asia/Kolkata")
TEMPLATES = ("S", "M", "L")


async def _params(session: AsyncSession) -> engine.EngineParams:
    rules = await library.engine_rules(session)
    try:
        bed, parcel = rules["engine.bed"], rules["engine.parcel"]
        border = rules["engine.border"]
        shares = {
            t: {
                k: float(v) for k, v in rules[f"engine.template.{t}"].items() if k != "applies_when"
            }
            for t in TEMPLATES
        }
    except KeyError as exc:
        raise AppError("RULES_MISSING", 500, {"rule": str(exc)}) from exc

    async def setting(key: str) -> float:
        return float(await get_setting(session, f"layout.{key}"))

    return engine.EngineParams(
        bed_width_m=float(bed["bed_width_m"]),
        path_width_m=float(bed["path_width_m"]),
        max_bed_length_m=float(bed["max_bed_length_m"]),
        min_bed_area_sqm=float(bed["min_bed_area_sqm"]),
        min_bed_width_m=float(bed["min_bed_width_m"]),
        bed_axis_tolerance_deg=float(bed["bed_axis_tolerance_deg"]),
        min_area_sqm=float(parcel["min_area_sqm"]),
        max_area_sqm=float(parcel["max_area_sqm"]),
        obstacle_buffer_m=float(parcel["obstacle_buffer_m"]),
        border_m={t: float(border[t]) for t in TEMPLATES},
        shares=shares,
        gate_opening_m=await setting("gate_opening_m"),
        nursery_share_of_utility=await setting("nursery_share_of_utility"),
        zone_aspect=await setting("zone_aspect"),
        area_tolerance_pct=await setting("area_tolerance_pct"),
        min_beds_share_pct=await setting("min_beds_share_pct"),
        min_beds_axis_extent_m=await setting("min_beds_axis_extent_m"),
    )


async def _planting_params(session: AsyncSession) -> planting.PlantingParams:
    rules = await library.engine_rules(session)
    try:
        score, crowding = rules["engine.score"], rules["engine.crowding"]
        min_crops, seasons = rules["engine.min_crops"], rules["engine.seasons"]
    except KeyError as exc:
        raise AppError("RULES_MISSING", 500, {"rule": str(exc)}) from exc
    return planting.PlantingParams(
        weights={k: float(score[k]) for k in ("value", "diversity", "ease", "water")},
        goal_income_value=float(score["goal_income_value"]),
        goal_home_food_diversity=float(score["goal_home_food_diversity"]),
        repeat_diversity=float(score["repeat_diversity"]),
        crowding={k: float(v) for k, v in crowding.items()},
        min_crops={k: int(v) for k, v in min_crops.items()},
        seasons={k: {"from": str(v["from"]), "to": str(v["to"])} for k, v in seasons.items()},
        plan_days=int(await get_setting(session, "layout.plan_days")),
        tall_crop_cm=int(await get_setting(session, "layout.tall_crop_cm")),
        good_companion_bonus=float(await get_setting(session, "layout.good_companion_bonus")),
        medicinal_bed_share=float(await get_setting(session, "layout.medicinal_bed_share")),
    )


def _crop_spec(c: EngineCrop) -> planting.CropSpec:
    return planting.CropSpec(
        slug=c.slug, status=c.status, family=c.family, layers=tuple(c.layers),
        seasons=tuple(c.seasons),
        sow_windows=tuple(
            (str(w.get("from")), str(w.get("to")), str(w.get("method", ""))) for w in c.sow_windows
        ),
        days_to_first_harvest=c.days_to_first_harvest, harvest_span_days=c.harvest_span_days,
        spacing_row_cm=c.spacing_row_cm, spacing_plant_cm=c.spacing_plant_cm,
        height_max_cm=c.height_max_cm, water_need=c.water_need,
        waterlogging_tolerant=c.waterlogging_tolerant, yield_kg_per_sqm=c.expected_yield_kg_per_sqm,
        low_care=c.low_care, price_paise_per_kg=c.price_direct_paise_per_kg,
        category=c.category, tags=tuple(c.tags),
    )  # fmt: skip


def _perennials(
    plants: list[Any], names: dict[uuid.UUID, Any], yields: dict[uuid.UUID, float | None]
) -> list[PerennialOut]:
    groups: dict[tuple[uuid.UUID, str], list[Any]] = {}
    for zp in plants:
        groups.setdefault((zp.crop_id, zp.kind), []).append(zp)
    out = []
    for (crop_id, kind), rows in groups.items():
        n = names.get(crop_id)
        if n is None:
            continue
        spacing = float(rows[0].spacing_m)
        per_sqm = yields.get(crop_id)
        out.append(
            PerennialOut(
                crop=CropRef(id=n.id, slug=n.slug, name_en=n.name_en, name_hi=n.name_hi,
                             ai_checked=n.status == "ai_verified"),
                kind=kind, count=len(rows), spacing_m=spacing,
                plant_on=min(r.plant_on for r in rows),
                first_harvest=min((r.first_harvest for r in rows if r.first_harvest), default=None),
                yearly_kg_when_bearing=(
                    round(per_sqm * spacing**2 * len(rows), 1)
                    if per_sqm is not None and kind == "tree" else None
                ),
                points={"type": "MultiPoint",
                        "coordinates": [list(to_shape(r.geom).coords[0]) for r in rows]},
            )
        )  # fmt: skip
    return sorted(out, key=lambda p: (p.kind, -p.count, p.crop.slug))


def _num(rule: dict[str, object], key: str) -> float | None:
    value = rule.get(key)
    return float(value) if isinstance(value, int | float) else None


async def _out(session: AsyncSession, plan: Plan) -> PlanOut:
    rules = await library.engine_rules(session)
    bed_rule = rules.get("engine.bed", {})
    zones = await repo.zones_of(session, plan.id)
    beds = await repo.beds_of(session, plan.id)
    layers = await repo.bed_layers_of(session, plan.id)
    plants = await repo.zone_plants_of(session, plan.id)
    names = await library.crop_names(
        session, list({bl.crop_id for _, bl in layers} | {zp.crop_id for zp in plants})
    )
    yields = {c.id: c.expected_yield_kg_per_sqm for c in await library.engine_crops(session)}
    summary = plan.summary
    return PlanOut(
        id=plan.id,
        option=plan.option,
        custom=bool(summary.get("custom")),
        bed_size=str(plan.inputs.get("bed_size", "standard")),
        share_delta={k: int(v) for k, v in (plan.inputs.get("owner_delta") or {}).items()},
        farm_id=plan.farm_id,
        version=plan.version,
        status=plan.status,
        start_date=plan.start_date,
        engine_version=plan.engine_version,
        template=summary.get("template", ""),
        area_sqm=float(summary.get("area_sqm", 0)),
        warnings=[PlanWarning(**w) for w in summary.get("warnings", [])],
        zones=[
            ZoneOut(
                id=z.id, kind=z.kind, label=z.label, area_sqm=float(z.area_sqm),
                geometry=repo.geojson(z.geom),
            )
            for z in zones
        ],
        beds=[
            BedOut(
                id=b.id, zone_id=b.zone_id, code=b.code, length_m=float(b.length_m),
                width_m=float(b.width_m), raised=b.raised, has_trellis=b.has_trellis,
                orientation_deg=float(b.orientation_deg), geometry=repo.geojson(b.geom),
                protected=b.protected,
            )
            for b in beds
        ],
        seasons=[SeasonOut(**s) for s in summary.get("seasons", [])],
        plantings=[
            PlantingOut(
                bed_code=code, season=bl.season, season_label=bl.season_label, layer=bl.layer,
                crop=CropRef(
                    id=bl.crop_id, slug=names[bl.crop_id].slug, name_en=names[bl.crop_id].name_en,
                    name_hi=names[bl.crop_id].name_hi,
                    ai_checked=names[bl.crop_id].status == "ai_verified",
                ),
                planned_sow=bl.planned_sow, harvest_start=bl.harvest_start,
                harvest_end=bl.harvest_end, plant_count=bl.plant_count, spacing_cm=bl.spacing_cm,
                expected_yield_kg=float(bl.expected_yield_kg), why=bl.why,
            )
            for code, bl in layers
            if bl.crop_id in names
        ],
        perennials=_perennials(plants, names, yields),
        uses_ai_checked=bool(summary.get("uses_ai_checked", False)),
        trellis_height_m=_num(bed_rule, "trellis_height_m"),
        bed_width_m=_num(bed_rule, "bed_width_m"),
        path_width_m=_num(bed_rule, "path_width_m"),
        machan_guide=list(rules.get("guide.machan", {}).get("steps", [])),
        created_at=plan.created_at,
    )  # fmt: skip


OPTION_ZONES = ("orchard", "water", "utility_nursery", "rotation")


async def _options_rule(session: AsyncSession) -> dict[str, Any]:
    rule = (await library.engine_rules(session)).get("engine.options")
    if not rule:
        raise AppError("RULES_MISSING", 500, {"rule": "engine.options"})
    return rule


def _suits(option: dict[str, Any], farm: FarmOut) -> list[str]:
    """Why an option suits this farm: its goal, who works it, its water."""
    match = option.get("for", {})
    out = []
    if farm.goal and farm.goal in match.get("goal", []):
        out.append("goal")
    if farm.labour and farm.labour in match.get("labour", []):
        out.append("labour")
    if farm.water_source and farm.water_source in match.get("water_source", []):
        out.append("water")
    if set(farm.methods or []) & set(match.get("methods", [])):
        out.append("methods")
    return out


async def _bed_widths(session: AsyncSession) -> dict[str, float]:
    raw = await get_setting(session, "layout.bed_widths")
    return {k: float(v) for k, v in raw.items()}


async def _build(
    session: AsyncSession,
    m: Membership,
    *,
    option: str,
    batch: int,
    owner_delta: dict[str, int] | None = None,
    bed_size: str = "standard",
) -> Plan:
    """Run the engine for one plan option (plus the owner's changes) and store the plan."""
    if not await parcel_service.parcel_exists(session, m.farm_id):
        raise AppError("PARCEL_REQUIRED", 409)
    parcel = await parcel_service.get_parcel(session, m)
    farm = await farms_service.get_farm(session, m)
    options = (await _options_rule(session))["options"]
    if option not in options:
        raise AppError("UNKNOWN_OPTION", 422, {"option": option})
    spec = options[option]
    owner_delta = {k: int(v) for k, v in (owner_delta or {}).items() if k in OPTION_ZONES}
    max_points = int(
        (await library.engine_rules(session))
        .get("engine.zone_share_adjust", {})
        .get("max_points", 10)
    )
    if any(abs(v) > max_points for v in owner_delta.values()):
        raise AppError("SHARE_CHANGE_TOO_BIG", 422, {"max_points": max_points})
    widths = await _bed_widths(session)
    if bed_size not in widths:
        raise AppError("UNKNOWN_BED_SIZE", 422, {"bed_size": bed_size})

    base = await _params(session)
    shares = {
        t: {
            k: max(0.0, v + spec.get("share_delta", {}).get(k, 0) + owner_delta.get(k, 0))
            if k in (*OPTION_ZONES, "beds") else v
            for k, v in zone_shares.items()
        }
        for t, zone_shares in base.shares.items()
    }  # fmt: skip
    # zones the owner asked for in the goal step (polyhouse; integrated farming -> livestock area)
    extra_sizes = {
        k: float(v) for k, v in (await get_setting(session, "layout.extra_zones")).items()
    }
    wanted = {"polyhouse": "polyhouse", "integrated": "livestock"}
    extra = {
        zone: extra_sizes[zone] for method, zone in wanted.items()
        if method in (farm.methods or []) and zone in extra_sizes
    }  # fmt: skip
    params = dataclasses.replace(
        base, shares=shares, bed_width_m=widths[bed_size], extra_zones=extra
    )
    site = engine.SiteInputs(
        boundary=parcel.boundary, north_bearing_deg=parcel.north_bearing_deg, gate=parcel.gate,
        slope_dir=parcel.slope_dir, drainage=parcel.drainage, soil_type=parcel.soil_type,
        obstacles=parcel.obstacles,
    )  # fmt: skip
    try:
        result = await asyncio.to_thread(engine.generate, site, params)
    except engine.LayoutError as exc:
        raise AppError(exc.code, 422, exc.details) from exc

    # 8. crops per bed, layer and season, with this option's score weights
    start_date = datetime.now(IST).date()
    crops = await library.engine_crops(session)
    companions = await library.engine_companions(session)
    crop_ids = {c.slug: c.id for c in crops}
    specs = {c.slug: _crop_spec(c) for c in crops}
    bed_specs = [
        planting.BedSpec(
            code=b.code, area_sqm=b.geom.area, length_m=b.length_m, width_m=b.width_m,
            raised=b.raised, has_trellis=b.has_trellis,
        )
        for b in result.beds
    ]  # fmt: skip
    crop_plan = planting.assign(
        bed_specs,
        list(specs.values()),
        [(c.crop_a, c.crop_b, c.relation) for c in companions],
        start=start_date,
        template=result.template,
        goal=farm.goal,
        drainage=parcel.drainage,
        p=await _planting_params(session),
        weights={k: float(v) for k, v in spec.get("weights", {}).items()} or None,
        allow_flowers="flowers" in (farm.methods or []),
        allow_medicinal="medicinal" in (farm.methods or []),
    )
    # trees in the orchard strip, hedge plants on the border
    pp = await _planting_params(session)
    tree_weights = {**pp.weights, **{k: float(v) for k, v in spec.get("weights", {}).items()}}
    trees = [
        perennials.PerennialSpec(specs[c.slug], float(c.tree_spacing_m), c.years_to_bear, None)
        for c in crops
        if c.category in ("fruit_tree", "fruit_short") and c.tree_spacing_m
        and c.years_to_bear is not None
    ]  # fmt: skip
    hedges = [
        perennials.PerennialSpec(specs[c.slug], c.spacing_plant_cm / 100, None,
                                 c.days_to_first_harvest)
        for c in crops if c.category == "border" and c.spacing_plant_cm
    ]  # fmt: skip
    orchard = [(i, z.geom) for i, z in enumerate(result.zones) if z.kind == "orchard"]
    border_index = next((i for i, z in enumerate(result.zones) if z.kind == "border"), None)
    orchard_rule = (await library.engine_rules(session)).get("engine.orchard", {})
    placed = perennials.plant_orchard(
        orchard, trees, weights=tree_weights, start=start_date, plan_days=pp.plan_days,
        max_species=int(spec.get("tree_species", 3)),
        max_short_lived=int(orchard_rule.get("max_short_lived", 1)),
        short_lived_max_years=float(orchard_rule.get("short_lived_max_years", 1)),
    )  # fmt: skip
    if border_index is not None:
        placed += perennials.plant_hedge(
            result.hedge_line, border_index, hedges, weights=tree_weights, gate=result.gate,
            gate_gap_m=result.gate_gap_m, start=start_date, plan_days=pp.plan_days,
        )  # fmt: skip
    per_season: dict[str, set[str]] = {}
    for pl in crop_plan.plantings:
        per_season.setdefault(pl.slot.label, set()).add(pl.crop)
    metrics = {
        "beds": len(result.beds),
        "bed_area_sqm": round(sum(b.geom.area for b in result.beds), 1),
        "crops_total": len({pl.crop for pl in crop_plan.plantings}),
        "crops_min_season": min((len(v) for v in per_season.values()), default=0),
        "harvest_kg": round(sum(pl.expected_yield_kg for pl in crop_plan.plantings), 1),
        "water_index": round(
            sum(
                next(b.area_sqm for b in bed_specs if b.code == pl.bed)
                * planting.WATER_LEVEL.get(specs[pl.crop].water_need or "medium", 0.5)
                * (pl.harvest_end - pl.planned_sow).days
                for pl in crop_plan.plantings
            ) / 1000, 1,
        ),
        # bed area under crops over the year: what has to be sown, weeded, watered and picked
        "work_index": round(
            sum(
                next(b.area_sqm for b in bed_specs if b.code == pl.bed)
                * (pl.harvest_end - pl.planned_sow).days
                for pl in crop_plan.plantings
            ) / 1000, 1,
        ),
        "plantings": len(crop_plan.plantings),
        "trees": sum(1 for x in placed if x.kind == "tree"),
        "tree_species": len({x.crop for x in placed if x.kind == "tree"}),
        "hedge_plants": sum(1 for x in placed if x.kind == "hedge"),
        "trees_yearly_kg": round(
            sum((specs[x.crop].yield_kg_per_sqm or 0) * x.spacing_m**2 for x in placed
                if x.kind == "tree"), 1,
        ),
    }  # fmt: skip

    plan = await repo.add_plan(
        session,
        farm_id=m.farm_id,
        version=await repo.next_version(session, m.farm_id),
        start_date=start_date,
        engine_version=engine.ENGINE_VERSION,
        option=option,
        batch=batch,
        inputs={
            "parcel_updated_at": parcel.updated_at.isoformat(),
            "area_sqm": parcel.area_sqm,
            "option": option,
            "owner_delta": owner_delta,
            "bed_size": bed_size,
            "params": {k: v for k, v in params.__dict__.items()},
        },
        summary={
            "engine_version": engine.ENGINE_VERSION,
            "template": result.template,
            "area_sqm": round(result.area_sqm, 2),
            "zones": [
                {"kind": z.kind, "label": z.label, "area_sqm": round(z.area_sqm, 2)}
                for z in result.zones
            ],
            "bed_count": len(result.beds),
            "warnings": result.warnings + crop_plan.warnings,
            "seasons": [
                {
                    "season": x.season,
                    "label": x.label,
                    "begin": x.begin.isoformat(),
                    "end": x.end.isoformat(),
                }
                for x in crop_plan.slots
            ],
            "uses_ai_checked": crop_plan.uses_ai_verified,
            "crops": sorted({pl.crop for pl in crop_plan.plantings}),
            "metrics": metrics,
            "custom": bool(owner_delta) or bed_size != "standard",
        },
        created_by=m.user_id,
    )
    zone_ids = []
    for z in result.zones:
        row = await repo.add_zone(
            session, plan.id, z.kind, z.label, result.frame.to_wgs84(z.geom), z.area_sqm
        )
        zone_ids.append(row.id)
    bed_ids = {}
    for b in result.beds:
        bed_row = await repo.add_bed(
            session, zone_ids[b.zone_index], code=b.code, geom=result.frame.to_wgs84(b.geom),
            length_m=b.length_m, width_m=b.width_m, raised=b.raised,
            orientation_deg=b.orientation_deg, has_trellis=b.has_trellis, protected=b.protected,
        )  # fmt: skip
        bed_ids[b.code] = bed_row.id
    for x in placed:
        await repo.add_zone_plant(
            session, zone_id=zone_ids[x.zone_index], crop_id=crop_ids[x.crop], kind=x.kind,
            geom=result.frame.to_wgs84(x.point), spacing_m=round(x.spacing_m, 2),
            plant_on=x.plant_on, first_harvest=x.first_harvest,
        )  # fmt: skip
    for pl in crop_plan.plantings:
        await repo.add_bed_layer(
            session, bed_id=bed_ids[pl.bed], layer=pl.layer, season=pl.slot.season,
            season_label=pl.slot.label, crop_id=crop_ids[pl.crop], planned_sow=pl.planned_sow,
            harvest_start=pl.harvest_start, harvest_end=pl.harvest_end,
            plant_count=pl.plant_count, spacing_cm=pl.spacing_cm,
            expected_yield_kg=pl.expected_yield_kg, why=pl.why,
        )  # fmt: skip
    await session.flush()
    return plan


def _levels(values: list[float]) -> list[Level]:
    """low / medium / high for each value against the middle option (more than 15% either side
    of the median; decision 2026-10-06)."""
    ordered = sorted(values)
    mid = ordered[len(ordered) // 2] if ordered else 0
    out: list[Level] = []
    for v in values:
        out.append("low" if v < 0.85 * mid else "high" if v > 1.15 * mid else "medium")
    return out


async def list_options(session: AsyncSession, m: Membership) -> OptionsOut:
    plans = await repo.latest_batch(session, m.farm_id)
    active = await repo.active_plan(session, m.farm_id)
    if active and all(p.id != active.id for p in plans):
        plans = [active, *plans]
    rule = await _options_rule(session)
    order = list(rule.get("order", []))
    farm = await farms_service.get_farm(session, m)
    plans = [p for p in plans if p.option and p.summary.get("metrics")]
    plans.sort(key=lambda p: (order.index(p.option) if p.option in order else 99, p.version))
    suits = {p.id: _suits(rule["options"].get(p.option or "", {}), farm) for p in plans}
    goal_match = next((p.option for p in plans if "goal" in suits[p.id]), None)
    recommended = goal_match or next((p.option for p in plans if suits[p.id]), "balanced")
    metrics = [OptionMetrics(**p.summary["metrics"]) for p in plans]
    harvest = _levels([x.harvest_kg for x in metrics])
    water = _levels([x.water_index for x in metrics])
    work = _levels([x.work_index for x in metrics])
    out = []
    for i, p in enumerate(plans):
        total = float(p.summary.get("area_sqm") or 1)
        land: dict[str, float] = {}
        for z in p.summary.get("zones", []):
            land[z["kind"]] = round(land.get(z["kind"], 0) + z["area_sqm"] / total, 3)
        out.append(
            OptionOut(
                plan_id=p.id, option=p.option or "", status=p.status,
                custom=bool(p.summary.get("custom")),
                recommended=p.option == recommended and not p.summary.get("custom"),
                suits=suits[p.id], metrics=metrics[i],
                levels={"harvest": harvest[i], "water": water[i], "work": work[i]},
                land_use=land,
            )
        )  # fmt: skip
    return OptionsOut(
        batch=plans[-1].batch if plans else None,
        active_plan_id=active.id if active else None,
        options=out,
    )


async def build_options(session: AsyncSession, m: Membership) -> OptionsOut:
    """Build every plan option side by side (spec 7 engine, one run per option)."""
    rule = await _options_rule(session)
    await repo.archive_drafts(session, m.farm_id)
    batch = await repo.next_batch(session, m.farm_id)
    for option in rule.get("order", []):
        await _build(session, m, option=option, batch=batch)
    return await list_options(session, m)


async def _plan_or_404(session: AsyncSession, m: Membership, plan_id: uuid.UUID) -> Plan:
    plan = await repo.get_plan(session, m.farm_id, plan_id)
    if plan is None:
        raise not_found("plan")
    return plan


async def get_plan(
    session: AsyncSession, m: Membership, plan_id: uuid.UUID | None = None
) -> PlanOut:
    """A given plan, else the active plan, else the recommended option of the latest build."""
    if plan_id:
        return await _out(session, await _plan_or_404(session, m, plan_id))
    plan = await repo.active_plan(session, m.farm_id)
    if plan is None:
        options = await list_options(session, m)
        pick = next((o for o in options.options if o.recommended), None) or next(
            iter(options.options), None
        )
        plan = await repo.get_plan(session, m.farm_id, pick.plan_id) if pick else None
    plan = plan or await repo.latest_plan(session, m.farm_id)
    if plan is None:
        raise not_found("plan")
    return await _out(session, plan)


async def adjust(
    session: AsyncSession, m: Membership, plan_id: uuid.UUID, data: AdjustIn
) -> PlanOut:
    """Re-run an option with the owner's land-use changes and bed size; a new draft plan."""
    source = await _plan_or_404(session, m, plan_id)
    plan = await _build(
        session, m, option=source.option or "balanced",
        batch=source.batch or await repo.next_batch(session, m.farm_id),
        owner_delta={str(k): v for k, v in data.share_delta.items()}, bed_size=data.bed_size,
    )  # fmt: skip
    return await _out(session, plan)


async def lock(session: AsyncSession, m: Membership, plan_id: uuid.UUID) -> PlanOut:
    """Make this plan the farm's active plan (the previous active one is archived)."""
    plan = await _plan_or_404(session, m, plan_id)
    await repo.set_active(session, m.farm_id, plan.id)
    await session.flush()
    await session.refresh(plan)
    return await _out(session, plan)


_GEOD = Geod(ellps="WGS84")


async def _bed_context(
    session: AsyncSession,
    m: Membership,
    plan_id: uuid.UUID,
    code: str,
    season_label: str,
    layer: str,
) -> tuple[Plan, Any, planting.BedSpec, planting.SeasonSlot, dict[str, Any]]:
    plan = await _plan_or_404(session, m, plan_id)
    bed = await repo.bed_in_plan(session, plan.id, code)
    if bed is None:
        raise not_found("bed")
    slots = [
        planting.SeasonSlot(s["season"], s["label"], date.fromisoformat(s["begin"]),
                            date.fromisoformat(s["end"]))
        for s in plan.summary.get("seasons", [])
    ]  # fmt: skip
    slot = next((s for s in slots if s.label == season_label), None)
    if slot is None:
        raise AppError("UNKNOWN_SEASON", 422, {"season": season_label})
    area = abs(_GEOD.geometry_area_perimeter(to_shape(bed.geom))[0])
    spec = planting.BedSpec(
        code=bed.code, area_sqm=area, length_m=float(bed.length_m), width_m=float(bed.width_m),
        raised=bed.raised, has_trellis=bed.has_trellis,
    )  # fmt: skip
    rows = await repo.layers_of_bed(session, bed.id)
    crops = {c.slug: c for c in await library.engine_crops(session)}
    by_id = {c.id: c for c in crops.values()}
    idx = [s.label for s in slots].index(slot.label)
    prev_label = slots[idx - 1].label if idx > 0 else None
    same_layer = sorted((r for r in rows if r.layer == layer), key=lambda r: r.planned_sow)
    current = next((r for r in same_layer if r.season_label == season_label), None)
    before = [
        r for r in same_layer if r.season_label != season_label and r.planned_sow < slot.begin
    ]
    after = [r for r in same_layer if r.season_label != season_label and r.planned_sow > slot.begin]
    ctx = {
        "crops": crops,
        "current": current,
        "others": [by_id[r.crop_id].slug for r in rows
                   if r.season_label == season_label and r.layer != layer and r.crop_id in by_id],
        "previous_families": {
            by_id[r.crop_id].family or by_id[r.crop_id].slug
            for r in rows if r.season_label == prev_label and r.crop_id in by_id
        },
        "free_from": before[-1].harvest_end if before and before[-1].harvest_end else None,
        "must_end_by": after[0].planned_sow if after else None,
    }  # fmt: skip
    return plan, bed, spec, slot, ctx


async def alternatives(
    session: AsyncSession,
    m: Membership,
    plan_id: uuid.UUID,
    code: str,
    season_label: str,
    layer: str,
) -> list[AlternativeOut]:
    """Crops that could replace the planned one in this bed layer and season."""
    _plan, _bed, spec, slot, ctx = await _bed_context(
        session, m, plan_id, code, season_label, layer
    )
    parcel = await parcel_service.get_parcel(session, m)
    companions = await library.engine_companions(session)
    options = planting.alternatives(
        spec, layer, slot, [_crop_spec(c) for c in ctx["crops"].values()],
        [(c.crop_a, c.crop_b, c.relation) for c in companions],
        others_in_bed=ctx["others"], previous_families=ctx["previous_families"],
        free_from=ctx["free_from"], must_end_by=ctx["must_end_by"], drainage=parcel.drainage,
        p=await _planting_params(session),
    )  # fmt: skip
    current = ctx["current"]
    out = []
    for o in options:
        c = ctx["crops"][o.crop]
        out.append(
            AlternativeOut(
                crop=CropRef(id=c.id, slug=c.slug, name_en=c.name_en, name_hi=c.name_hi,
                             ai_checked=c.status == "ai_verified"),
                current=bool(current and current.crop_id == c.id),
                planned_sow=o.planned_sow, harvest_start=o.harvest_start,
                harvest_end=o.harvest_end, plant_count=o.plant_count,
                expected_yield_kg=o.expected_yield_kg,
            )
        )  # fmt: skip
    return out


async def swap(
    session: AsyncSession, m: Membership, plan_id: uuid.UUID, code: str, data: SwapIn
) -> PlanOut:
    """Put the owner's chosen crop in a bed layer (only crops that pass every rule there)."""
    allowed = await alternatives(session, m, plan_id, code, data.season_label, data.layer)
    pick = next((a for a in allowed if a.crop.slug == data.crop_slug), None)
    if pick is None:
        raise AppError("CROP_NOT_ALLOWED_HERE", 422, {"crop": data.crop_slug})
    plan, bed, _spec, slot, ctx = await _bed_context(
        session, m, plan_id, code, data.season_label, data.layer
    )
    crop = ctx["crops"][data.crop_slug]
    values = {
        "crop_id": crop.id, "planned_sow": pick.planned_sow, "harvest_start": pick.harvest_start,
        "harvest_end": pick.harvest_end, "plant_count": pick.plant_count,
        "spacing_cm": crop.spacing_plant_cm or 0, "expected_yield_kg": pick.expected_yield_kg,
        "why": {"key": "plan.why.owner"},
    }  # fmt: skip
    current = ctx["current"]
    if current is not None:
        for k, v in values.items():
            setattr(current, k, v)
    else:
        await repo.add_bed_layer(
            session, bed_id=bed.id, layer=data.layer, season=slot.season,
            season_label=slot.label, **values,
        )  # fmt: skip
    plan.summary = {**plan.summary, "custom": True}
    await session.flush()
    return await _out(session, plan)


ZONE_TAGS = {"beds": "beds", "orchard": "orchard", "water": "pond", "utility": "utility",
             "nursery": "nursery", "rotation": "rotation", "polyhouse": "polyhouse",
             "livestock": "livestock"}  # fmt: skip


async def benefits(session: AsyncSession, m: Membership, plan_id: uuid.UUID) -> list[SchemeOut]:
    """Government schemes this plan and farm may be eligible for (vision pillar 6)."""
    plan = await _plan_or_404(session, m, plan_id)
    farm = await farms_service.get_farm(session, m)
    kinds = {z.get("kind") for z in plan.summary.get("zones", [])}
    tags = {"all", *(ZONE_TAGS[k] for k in kinds if k in ZONE_TAGS)}
    if farm.goal:
        tags.add(f"goal:{farm.goal}")
    if "medicinal" in (farm.methods or []):
        tags.add("medicinal")
    if plan.option:
        tags.add(f"option:{plan.option}")
    facts = {
        "electricity": farm.electricity, "water_source": farm.water_source,
        "labour": farm.labour, "goal": farm.goal,
    }  # fmt: skip
    return await site_service.schemes_for(session, tags, facts)
