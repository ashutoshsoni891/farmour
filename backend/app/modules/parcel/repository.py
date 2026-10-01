"""Database access for parcels. Only this module imports it."""

import uuid
from typing import Any

from geoalchemy2.shape import from_shape
from shapely.geometry.base import BaseGeometry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.parcel.models import Parcel


async def get_for_farm(session: AsyncSession, farm_id: uuid.UUID) -> Parcel | None:
    return await session.scalar(select(Parcel).where(Parcel.farm_id == farm_id))


async def save(
    session: AsyncSession,
    *,
    farm_id: uuid.UUID,
    actor: uuid.UUID,
    boundary: BaseGeometry,
    area_sqm: float,
    perimeter_m: float,
    gate: BaseGeometry | None,
    options: dict[str, Any],
) -> Parcel:
    parcel = await get_for_farm(session, farm_id)
    if parcel is None:
        parcel = Parcel(id=uuid.uuid4(), farm_id=farm_id, created_by=actor)
        session.add(parcel)
    parcel.boundary = from_shape(boundary, srid=4326)
    parcel.area_sqm = round(area_sqm, 2)  # type: ignore[assignment]
    parcel.perimeter_m = round(perimeter_m, 2)  # type: ignore[assignment]
    if gate is not None:
        parcel.gate = from_shape(gate, srid=4326)
    for key, value in options.items():
        setattr(parcel, key, value)
    await session.flush()
    await session.refresh(parcel)
    return parcel
