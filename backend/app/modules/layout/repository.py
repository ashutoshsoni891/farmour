"""Database access for the layout module. Only this module imports it."""

import uuid
from datetime import date
from typing import Any

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Polygon, mapping
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.layout.models import Bed, Plan, Zone


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
) -> Plan:
    plan = Plan(
        id=uuid.uuid4(), farm_id=farm_id, version=version, status="draft", start_date=start_date,
        engine_version=engine_version, inputs=inputs, summary=summary, created_by=created_by,
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
    return bed


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
