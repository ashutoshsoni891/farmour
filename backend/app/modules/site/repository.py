"""Database access for site intelligence. Only this module imports it."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Region
from app.modules.site.models import (
    CostNorm,
    DistrictRegion,
    GeoCache,
    GroundwaterBlock,
    Kvk,
    Mandi,
    MandiPrice,
    MarketCentre,
    Scheme,
    SiteBuild,
    SiteFact,
)

USER_SOURCES = ("user", "soil_test")


async def facts_for_farm(session: AsyncSession, farm_id: uuid.UUID) -> list[SiteFact]:
    return list(await session.scalars(select(SiteFact).where(SiteFact.farm_id == farm_id)))


async def get_fact(
    session: AsyncSession, farm_id: uuid.UUID, key: str, source: str
) -> SiteFact | None:
    return await session.scalar(
        select(SiteFact).where(
            SiteFact.farm_id == farm_id, SiteFact.key == key, SiteFact.source == source
        )
    )


async def upsert_derived(session: AsyncSession, farm_id: uuid.UUID, fact: dict[str, Any]) -> bool:
    """Write a derived fact; never overwrite one the owner has confirmed or edited."""
    existing = await get_fact(session, farm_id, fact["key"], fact["source"])
    if existing is None:
        session.add(SiteFact(farm_id=farm_id, status="derived", **fact))
        return True
    if existing.status in ("confirmed", "edited", "rejected"):
        return False
    for k, v in fact.items():
        setattr(existing, k, v)
    return True


async def save_user_fact(
    session: AsyncSession,
    farm_id: uuid.UUID,
    *,
    key: str,
    value: Any,
    status: str,
    unit: str | None = None,
    source: str = "user",
) -> SiteFact:
    now = datetime.now(UTC)
    existing = await get_fact(session, farm_id, key, source)
    if existing is None:
        existing = SiteFact(
            farm_id=farm_id, key=key, source=source, confidence=Decimal("1.00"),
            fetched_at=now,
        )  # fmt: skip
        session.add(existing)
    existing.value, existing.status, existing.unit = value, status, unit
    existing.method = "owner"
    existing.fetched_at = now
    await session.flush()
    return existing


async def get_build(session: AsyncSession, farm_id: uuid.UUID) -> SiteBuild | None:
    return await session.get(SiteBuild, farm_id)


async def start_build(session: AsyncSession, farm_id: uuid.UUID) -> SiteBuild:
    build = await get_build(session, farm_id)
    if build is None:
        build = SiteBuild(farm_id=farm_id, status="running")
        session.add(build)
    build.status, build.started_at, build.finished_at, build.report = (
        "running", datetime.now(UTC), None, {},
    )  # fmt: skip
    await session.flush()
    return build


# ---- cache ----


async def get_cache(session: AsyncSession, cell: str, source: str) -> GeoCache | None:
    return await session.get(GeoCache, (cell, source))


async def put_cache(session: AsyncSession, cell: str, source: str, payload: Any) -> None:
    stmt = insert(GeoCache).values(
        cell_key=cell, source=source, payload=payload, fetched_at=datetime.now(UTC)
    )
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=["cell_key", "source"],
            set_={"payload": payload, "fetched_at": datetime.now(UTC)},
        )
    )


# ---- lookups ----


async def region_for_district(session: AsyncSession, state: str, district: str) -> Region | None:
    return await session.scalar(
        select(Region)
        .join(DistrictRegion, DistrictRegion.region_id == Region.id)
        .where(
            func.lower(DistrictRegion.state) == state.lower(),
            func.lower(DistrictRegion.district) == district.lower(),
        )
    )


async def groundwater_for_district(
    session: AsyncSession, state: str, district: str
) -> GroundwaterBlock | None:
    """District-level category (a row with no block)."""
    return await session.scalar(
        select(GroundwaterBlock).where(
            func.lower(GroundwaterBlock.state) == state.lower(),
            func.lower(GroundwaterBlock.district) == district.lower(),
            GroundwaterBlock.block.is_(None),
        )
    )


async def mandis_with_location(session: AsyncSession, state: str) -> list[Mandi]:
    return list(
        await session.scalars(
            select(Mandi).where(
                func.lower(Mandi.state) == state.lower(),
                Mandi.lat.is_not(None),
                Mandi.lng.is_not(None),
            )
        )
    )


async def mandis_to_geocode(session: AsyncSession, limit: int) -> list[Mandi]:
    return list(
        await session.scalars(
            select(Mandi).where(Mandi.lat.is_(None), Mandi.geocode_tried.is_(False)).limit(limit)
        )
    )


async def upsert_mandi(session: AsyncSession, name: str, district: str, state: str) -> uuid.UUID:
    stmt = (
        insert(Mandi)
        .values(id=uuid.uuid4(), name=name, district=district, state=state)
        .on_conflict_do_nothing(index_elements=["name", "district", "state"])
    )
    await session.execute(stmt)
    mandi_id = await session.scalar(
        select(Mandi.id).where(Mandi.name == name, Mandi.district == district, Mandi.state == state)
    )
    if mandi_id is None:
        raise RuntimeError("mandi upsert failed")
    return mandi_id


async def upsert_prices(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = (
        insert(MandiPrice)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["mandi_id", "commodity", "variety", "price_date"])
    )
    result = await session.execute(stmt)
    return int(getattr(result, "rowcount", 0) or 0)


async def add_all(session: AsyncSession, *rows: object) -> None:
    session.add_all(rows)
    await session.flush()


async def region_by_slug(session: AsyncSession, slug: str) -> Region | None:
    return await session.scalar(select(Region).where(Region.slug == slug))


async def schemes(session: AsyncSession, statuses: list[str]) -> list[Scheme]:
    return list(
        await session.scalars(
            select(Scheme).where(Scheme.status.in_(statuses)).order_by(Scheme.code)
        )
    )


async def cost_norms(session: AsyncSession, statuses: list[str]) -> list[CostNorm]:
    return list(
        await session.scalars(
            select(CostNorm)
            .where(CostNorm.status.in_(statuses))
            .order_by(CostNorm.group, CostNorm.code)
        )
    )


async def kvks(session: AsyncSession, statuses: list[str], district: str | None) -> list[Kvk]:
    stmt = select(Kvk).where(Kvk.status.in_(statuses))
    if district:
        stmt = stmt.where(func.lower(Kvk.district) == district.strip().lower())
    return list(await session.scalars(stmt.order_by(Kvk.state, Kvk.district, Kvk.code)))


async def market_centres(session: AsyncSession, statuses: list[str]) -> list[MarketCentre]:
    return list(
        await session.scalars(
            select(MarketCentre)
            .where(MarketCentre.status.in_(statuses))
            .order_by(MarketCentre.kind, MarketCentre.code)
        )
    )
