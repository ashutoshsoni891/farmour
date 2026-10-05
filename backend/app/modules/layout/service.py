"""Layout module public entry point: build and read a farm's plan (spec section 7)."""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, not_found
from app.core.settings_store import get_setting
from app.modules.farms import service as farms_service
from app.modules.farms.service import Membership
from app.modules.layout import engine, planting
from app.modules.layout import repository as repo
from app.modules.layout.models import Plan
from app.modules.layout.schemas import (
    BedOut,
    CropRef,
    PlanOut,
    PlantingOut,
    PlanWarning,
    SeasonOut,
    ZoneOut,
)
from app.modules.library import service as library
from app.modules.library.schemas import EngineCrop
from app.modules.parcel import service as parcel_service

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
    )  # fmt: skip


async def _out(session: AsyncSession, plan: Plan) -> PlanOut:
    zones = await repo.zones_of(session, plan.id)
    beds = await repo.beds_of(session, plan.id)
    layers = await repo.bed_layers_of(session, plan.id)
    names = await library.crop_names(session, list({bl.crop_id for _, bl in layers}))
    summary = plan.summary
    return PlanOut(
        id=plan.id,
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
                planned_sow=bl.planned_sow, plant_count=bl.plant_count, spacing_cm=bl.spacing_cm,
                expected_yield_kg=float(bl.expected_yield_kg), why=bl.why,
            )
            for code, bl in layers
            if bl.crop_id in names
        ],
        uses_ai_checked=bool(summary.get("uses_ai_checked", False)),
        created_at=plan.created_at,
    )  # fmt: skip


async def get_plan(session: AsyncSession, m: Membership) -> PlanOut:
    plan = await repo.latest_plan(session, m.farm_id)
    if plan is None:
        raise not_found("plan")
    return await _out(session, plan)


async def generate_plan(session: AsyncSession, m: Membership) -> PlanOut:
    """Build a new draft plan (layout: zones and beds) from the farm's plot."""
    if not await parcel_service.parcel_exists(session, m.farm_id):
        raise AppError("PARCEL_REQUIRED", 409)
    parcel = await parcel_service.get_parcel(session, m)
    params = await _params(session)
    site = engine.SiteInputs(
        boundary=parcel.boundary,
        north_bearing_deg=parcel.north_bearing_deg,
        gate=parcel.gate,
        slope_dir=parcel.slope_dir,
        drainage=parcel.drainage,
        soil_type=parcel.soil_type,
        obstacles=parcel.obstacles,
    )
    try:
        result = await asyncio.to_thread(engine.generate, site, params)
    except engine.LayoutError as exc:
        raise AppError(exc.code, 422, exc.details) from exc

    # 8. crops per bed, layer and season
    farm = await farms_service.get_farm(session, m)
    start_date = datetime.now(IST).date()
    crops = await library.engine_crops(session)
    companions = await library.engine_companions(session)
    crop_ids = {c.slug: c.id for c in crops}
    bed_specs = [
        planting.BedSpec(
            code=b.code, area_sqm=b.geom.area, length_m=b.length_m, width_m=b.width_m,
            raised=b.raised, has_trellis=b.has_trellis,
        )
        for b in result.beds
    ]  # fmt: skip
    crop_plan = planting.assign(
        bed_specs,
        [_crop_spec(c) for c in crops],
        [(c.crop_a, c.crop_b, c.relation) for c in companions],
        start=start_date,
        template=result.template,
        goal=farm.goal,
        drainage=parcel.drainage,
        p=await _planting_params(session),
    )

    await repo.archive_drafts(session, m.farm_id)
    plan = await repo.add_plan(
        session,
        farm_id=m.farm_id,
        version=await repo.next_version(session, m.farm_id),
        start_date=start_date,
        engine_version=engine.ENGINE_VERSION,
        inputs={
            "parcel_updated_at": parcel.updated_at.isoformat(),
            "area_sqm": parcel.area_sqm,
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
            orientation_deg=b.orientation_deg, has_trellis=b.has_trellis,
        )  # fmt: skip
        bed_ids[b.code] = bed_row.id
    for pl in crop_plan.plantings:
        await repo.add_bed_layer(
            session, bed_id=bed_ids[pl.bed], layer=pl.layer, season=pl.slot.season,
            season_label=pl.slot.label, crop_id=crop_ids[pl.crop], planned_sow=pl.planned_sow,
            plant_count=pl.plant_count, spacing_cm=pl.spacing_cm,
            expected_yield_kg=pl.expected_yield_kg, why=pl.why,
        )  # fmt: skip
    await session.flush()
    return await _out(session, plan)
