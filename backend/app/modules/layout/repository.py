"""Database access for the layout module. Only this module imports it."""

import uuid
from datetime import date
from typing import Any

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Polygon, mapping
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.layout.models import Bed, BedLayer, Plan, Zone


async def get_plan(session: AsyncSession, farm_id: uuid.UUID, plan_id: uuid.UUID) -> Plan | None:
    return await session.scalar(select(Plan).where(Plan.id == plan_id, Plan.farm_id == farm_id))


async def active_plan(session: AsyncSession, farm_id: uuid.UUID) -> Plan | None:
    return await session.scalar(
        select(Plan).where(Plan.farm_id == farm_id, Plan.status == "active").limit(1)
    )


async def latest_batch(session: AsyncSession, farm_id: uuid.UUID) -> list[Plan]:
    top = await session.scalar(
        select(func.max(Plan.batch)).where(Plan.farm_id == farm_id, Plan.status != "archived")
    )
    if top is None:
        return []
    return list(
        await session.scalars(
            select(Plan)
            .where(Plan.farm_id == farm_id, Plan.batch == top, Plan.status != "archived")
            .order_by(Plan.version)
        )
    )


async def next_batch(session: AsyncSession, farm_id: uuid.UUID) -> int:
    top = await session.scalar(select(func.max(Plan.batch)).where(Plan.farm_id == farm_id))
    return (top or 0) + 1


async def set_active(session: AsyncSession, farm_id: uuid.UUID, plan_id: uuid.UUID) -> None:
    await session.execute(
        update(Plan)
        .where(Plan.farm_id == farm_id, Plan.status == "active", Plan.id != plan_id)
        .values(status="archived")
    )
    await session.execute(update(Plan).where(Plan.id == plan_id).values(status="active"))


async def bed_in_plan(session: AsyncSession, plan_id: uuid.UUID, code: str) -> Bed | None:
    return await session.scalar(
        select(Bed)
        .join(Zone, Bed.zone_id == Zone.id)
        .where(Zone.plan_id == plan_id, Bed.code == code)
    )


async def layers_of_bed(session: AsyncSession, bed_id: uuid.UUID) -> list[BedLayer]:
    return list(
        await session.scalars(
            select(BedLayer).where(BedLayer.bed_id == bed_id).order_by(BedLayer.planned_sow)
        )
    )


async def latest_plan(session: AsyncSession, farm_id: uuid.UUID) -> Plan | None:
    return await session.scalar(
        select(Plan)
        .where(Plan.farm_id == farm_id, Plan.status != "archived")
        .order_by(Plan.version.desc())
        .limit(1)
    )


async def next_version(session: AsyncSession, farm_id: uuid.UUID) -> int:
    top = await session.scalar(select(func.max(Plan.version)).where(Plan.farm_id == farm_id))
    return (top or 0) + 1


async def archive_drafts(session: AsyncSession, farm_id: uuid.UUID) -> None:
    """Archive the farm's draft plans (the active plan is kept)."""
    await session.execute(
        update(Plan)
        .where(Plan.farm_id == farm_id, Plan.status == "draft")
        .values(status="archived")
    )


async def add_plan(
    session: AsyncSession,
    *,
    farm_id: uuid.UUID,
    version: int,
    start_date: date,
    engine_version: str,
    inputs: dict[str, Any],
    summary: dict[str, Any],
    created_by: uuid.UUID | None,
    option: str | None = None,
    batch: int | None = None,
) -> Plan:
    plan = Plan(
        id=uuid.uuid4(), farm_id=farm_id, version=version, status="draft", start_date=start_date,
        engine_version=engine_version, inputs=inputs, summary=summary, created_by=created_by,
        option=option, batch=batch,
    )  # fmt: skip
    session.add(plan)
    await session.flush()
    return plan


async def add_zone(
    session: AsyncSession, plan_id: uuid.UUID, kind: str, label: str, geom: Polygon, area: float
) -> Zone:
    zone = Zone(
        id=uuid.uuid4(), plan_id=plan_id, kind=kind, label=label, area_sqm=round(area, 2),
        geom=from_shape(geom, srid=4326),
    )  # fmt: skip
    session.add(zone)
    await session.flush()
    return zone


async def add_bed(
    session: AsyncSession,
    zone_id: uuid.UUID,
    *,
    code: str,
    geom: Polygon,
    length_m: float,
    width_m: float,
    raised: bool,
    orientation_deg: float,
    has_trellis: bool,
) -> Bed:
    bed = Bed(
        id=uuid.uuid4(), zone_id=zone_id, code=code, geom=from_shape(geom, srid=4326),
        length_m=round(length_m, 2), width_m=round(width_m, 2), raised=raised,
        orientation_deg=round(orientation_deg, 2), has_trellis=has_trellis,
    )  # fmt: skip
    session.add(bed)
    await session.flush()
    return bed


async def add_bed_layer(session: AsyncSession, **values: Any) -> None:
    session.add(BedLayer(id=uuid.uuid4(), **values))


async def bed_layers_of(session: AsyncSession, plan_id: uuid.UUID) -> list[tuple[str, BedLayer]]:
    rows = await session.execute(
        select(Bed.code, BedLayer)
        .join(Bed, BedLayer.bed_id == Bed.id)
        .join(Zone, Bed.zone_id == Zone.id)
        .where(Zone.plan_id == plan_id)
        .order_by(BedLayer.planned_sow, BedLayer.season_label)
    )
    return [(code, layer) for code, layer in rows.tuples()]


async def zones_of(session: AsyncSession, plan_id: uuid.UUID) -> list[Zone]:
    return list(
        await session.scalars(
            select(Zone).where(Zone.plan_id == plan_id).order_by(Zone.kind, Zone.label)
        )
    )


async def beds_of(session: AsyncSession, plan_id: uuid.UUID) -> list[Bed]:
    rows = await session.scalars(
        select(Bed).join(Zone, Bed.zone_id == Zone.id).where(Zone.plan_id == plan_id)
    )
    return sorted(rows, key=lambda b: (len(b.code), b.code))


def geojson(geom: Any) -> dict[str, Any]:
    return dict(mapping(to_shape(geom)))
