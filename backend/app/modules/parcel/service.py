"""Public entry point of the parcel module: save, read and measure a farm's plot."""

import uuid
from typing import Any

from geoalchemy2.shape import to_shape
from shapely.geometry import Point, shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import audit, events
from app.core.errors import AppError, not_found
from app.core.settings_store import get_setting
from app.modules.farms.service import Membership
from app.modules.parcel import geometry as geo
from app.modules.parcel import repository as repo
from app.modules.parcel.models import Parcel
from app.modules.parcel.schemas import (
    FourSides,
    MeasurementsSave,
    ParcelOptions,
    ParcelOut,
    ParcelSave,
    Rectangle,
)


async def _limits(session: AsyncSession) -> dict[str, float]:
    raw: dict[str, Any] = await get_setting(session, "parcel.limits")
    return {
        "min_area_sqm": float(raw["min_area_sqm"]),
        "max_area_sqm": float(raw["max_area_sqm"]),
        "min_side_m": float(raw["min_side_m"]),
    }


def _out(parcel: Parcel, warnings: list[str] | None = None) -> ParcelOut:
    return ParcelOut(
        id=parcel.id,
        farm_id=parcel.farm_id,
        boundary=geo.to_geojson(to_shape(parcel.boundary)),
        gate=geo.to_geojson(to_shape(parcel.gate)) if parcel.gate is not None else None,
        area_sqm=float(parcel.area_sqm),
        perimeter_m=float(parcel.perimeter_m) if parcel.perimeter_m is not None else None,
        north_bearing_deg=float(parcel.north_bearing_deg),
        soil_type=parcel.soil_type,
        soil_depth_cm=parcel.soil_depth_cm,
        drainage=parcel.drainage,
        slope_dir=parcel.slope_dir,
        terrace_load_kg_per_sqm=(
            float(parcel.terrace_load_kg_per_sqm)
            if parcel.terrace_load_kg_per_sqm is not None
            else None
        ),
        obstacles=parcel.obstacles,
        warnings=warnings or [],
        updated_at=parcel.updated_at,
    )


async def get_parcel(session: AsyncSession, m: Membership) -> ParcelOut:
    parcel = await repo.get_for_farm(session, m.farm_id)
    if parcel is None:
        raise not_found("parcel")
    return _out(parcel)


async def _store(
    session: AsyncSession, m: Membership, polygon: Any, options: ParcelOptions
) -> ParcelOut:
    try:
        measured = geo.measure(polygon, **await _limits(session))
    except geo.GeometryError as exc:
        raise AppError(exc.code, 422, exc.details) from exc

    values = options.model_dump(exclude_unset=True, exclude={"gate", "boundary", "shape"})
    gate = None
    if options.gate is not None:
        gate_geom = shape(options.gate)
        if not isinstance(gate_geom, Point):
            raise AppError("PARCEL_INVALID_GEOMETRY", 422, {"reason": "gate_must_be_a_point"})
        gate = gate_geom
    values.pop("obstacles", None)
    if options.obstacles is not None:
        values["obstacles"] = options.obstacles
    values = {k: v for k, v in values.items() if v is not None}

    existed = await repo.get_for_farm(session, m.farm_id) is not None
    parcel = await repo.save(
        session,
        farm_id=m.farm_id,
        actor=m.user_id,
        boundary=measured.polygon_wgs84,
        area_sqm=measured.area_sqm,
        perimeter_m=measured.perimeter_m,
        gate=gate,
        options=values,
    )
    await audit.record(
        session,
        actor_id=m.user_id,
        entity="parcel",
        entity_id=parcel.id,
        action="update" if existed else "create",
        after={"area_sqm": float(parcel.area_sqm)},
    )
    await events.publish(session, "parcel.saved", {"farm_id": str(m.farm_id)})
    return _out(parcel)


async def save_parcel(session: AsyncSession, m: Membership, data: ParcelSave) -> ParcelOut:
    try:
        polygon = geo.polygon_from_geojson(data.boundary)
    except geo.GeometryError as exc:
        raise AppError(exc.code, 422, exc.details) from exc
    return await _store(session, m, polygon, data)


async def save_from_measurements(
    session: AsyncSession, m: Membership, data: MeasurementsSave
) -> ParcelOut:
    s = data.shape
    try:
        if isinstance(s, Rectangle):
            polygon = geo.rectangle(s.lng, s.lat, s.length_m, s.width_m, s.bearing_deg)
        elif isinstance(s, FourSides):
            polygon = geo.quadrilateral(
                s.lng, s.lat, s.side_ab_m, s.side_bc_m, s.side_cd_m, s.side_da_m,
                s.diagonal_ac_m, s.bearing_deg,
            )  # fmt: skip
    except geo.GeometryError as exc:
        raise AppError(exc.code, 422, exc.details) from exc
    return await _store(session, m, polygon, data)


async def parcel_exists(session: AsyncSession, farm_id: uuid.UUID) -> bool:
    return await repo.get_for_farm(session, farm_id) is not None
