"""Database access for the library module. Only this module imports it."""

import uuid
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Region
from app.modules.library.models import (
    Companion,
    Crop,
    CropRegional,
    LibraryRevision,
    Pest,
    Recipe,
    Rule,
)

Entity = Crop | Recipe | Pest | Rule
ENTITY_NAMES: dict[type[Entity], str] = {Crop: "crop", Recipe: "recipe", Pest: "pest", Rule: "rule"}
ENTITY_MODELS: dict[str, type[Entity]] = {
    "crop": Crop,
    "recipe": Recipe,
    "pest": Pest,
    "rule": Rule,
}


async def region_by_slug(session: AsyncSession, slug: str) -> Region | None:
    return await session.scalar(select(Region).where(Region.slug == slug))


async def region_slugs(session: AsyncSession) -> dict[uuid.UUID, str]:
    return {r.id: r.slug for r in await session.scalars(select(Region))}


# ---- crops ----


async def get_crop(session: AsyncSession, crop_id: uuid.UUID) -> Crop | None:
    return await session.get(Crop, crop_id)


async def get_crop_by_slug(session: AsyncSession, slug: str) -> Crop | None:
    return await session.scalar(select(Crop).where(Crop.slug == slug))


async def list_crops(
    session: AsyncSession,
    *,
    statuses: list[str],
    q: str | None,
    category: str | None,
    after: str | None,
    limit: int,
) -> list[Crop]:
    stmt = select(Crop).where(Crop.status.in_(statuses)).order_by(Crop.slug).limit(limit)
    if after:
        stmt = stmt.where(Crop.slug > after)
    if category:
        stmt = stmt.where(Crop.category == category)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            (Crop.slug.ilike(like)) | (Crop.name_en.ilike(like)) | (Crop.name_hi.ilike(like))
        )
    return list(await session.scalars(stmt))


async def crop_slug_map(session: AsyncSession) -> dict[str, uuid.UUID]:
    rows = await session.execute(select(Crop.slug, Crop.id))
    return {slug: cid for slug, cid in rows.tuples()}


async def regional_for(
    session: AsyncSession, crop_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[CropRegional]]:
    out: dict[uuid.UUID, list[CropRegional]] = {}
    if not crop_ids:
        return out
    rows = await session.scalars(select(CropRegional).where(CropRegional.crop_id.in_(crop_ids)))
    for row in rows:
        out.setdefault(row.crop_id, []).append(row)
    return out


async def upsert_regional(
    session: AsyncSession, crop_id: uuid.UUID, region_id: uuid.UUID, values: dict[str, Any]
) -> CropRegional:
    row = await session.scalar(
        select(CropRegional).where(
            CropRegional.crop_id == crop_id, CropRegional.region_id == region_id
        )
    )
    if row is None:
        row = CropRegional(crop_id=crop_id, region_id=region_id)
        session.add(row)
    for key, value in values.items():
        setattr(row, key, value)
    await session.flush()
    return row


# ---- generic reviewed entities ----


async def get_entity(session: AsyncSession, entity: str, entity_id: uuid.UUID) -> Entity | None:
    return await session.get(ENTITY_MODELS[entity], entity_id)


async def list_in_review(session: AsyncSession) -> list[tuple[str, Entity]]:
    out: list[tuple[str, Entity]] = []
    for model in (Crop, Recipe, Pest, Rule):
        rows = await session.scalars(
            select(model).where(model.status == "in_review").order_by(model.submitted_at)
        )
        out.extend((ENTITY_NAMES[model], cast(Entity, row)) for row in rows)
    return out


async def add_revision(
    session: AsyncSession,
    entity: str,
    entity_id: uuid.UUID,
    revision: int,
    snapshot: dict[str, Any],
    approved_by: uuid.UUID | None,
) -> None:
    session.add(
        LibraryRevision(
            entity=entity,
            entity_id=entity_id,
            revision=revision,
            snapshot=snapshot,
            approved_by=approved_by,
            approved_at=datetime.now(UTC),
        )
    )
    await session.flush()


async def get_revision(
    session: AsyncSession, entity: str, entity_id: uuid.UUID, revision: int
) -> LibraryRevision | None:
    return await session.scalar(
        select(LibraryRevision).where(
            LibraryRevision.entity == entity,
            LibraryRevision.entity_id == entity_id,
            LibraryRevision.revision == revision,
        )
    )


# ---- recipes, pests, rules ----


async def get_recipe_by_slug(session: AsyncSession, slug: str) -> Recipe | None:
    return await session.scalar(select(Recipe).where(Recipe.slug == slug))


async def get_pest_by_slug(session: AsyncSession, slug: str) -> Pest | None:
    return await session.scalar(select(Pest).where(Pest.slug == slug))


async def get_rule_by_code(session: AsyncSession, code: str) -> Rule | None:
    return await session.scalar(select(Rule).where(Rule.code == code))


async def recipe_slug_map(session: AsyncSession) -> dict[str, uuid.UUID]:
    rows = await session.execute(select(Recipe.slug, Recipe.id))
    return {slug: rid for slug, rid in rows.tuples()}


async def list_recipes(session: AsyncSession, statuses: list[str]) -> list[Recipe]:
    return list(
        await session.scalars(
            select(Recipe).where(Recipe.status.in_(statuses)).order_by(Recipe.slug)
        )
    )


async def list_pests(session: AsyncSession, statuses: list[str]) -> list[Pest]:
    return list(
        await session.scalars(select(Pest).where(Pest.status.in_(statuses)).order_by(Pest.slug))
    )


async def list_rules(session: AsyncSession, statuses: list[str]) -> list[Rule]:
    return list(
        await session.scalars(select(Rule).where(Rule.status.in_(statuses)).order_by(Rule.code))
    )


# ---- companions ----


async def list_companions(session: AsyncSession, statuses: list[str]) -> list[Companion]:
    return list(await session.scalars(select(Companion).where(Companion.status.in_(statuses))))


async def get_companion_pair(session: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> Companion | None:
    return await session.scalar(
        select(Companion).where(Companion.crop_a == a, Companion.crop_b == b)
    )


async def add_all(session: AsyncSession, *rows: object) -> None:
    session.add_all(rows)
    await session.flush()


async def count_approved(session: AsyncSession) -> dict[str, int]:
    out = {}
    for name, model in (("crops", Crop), ("recipes", Recipe), ("pests", Pest)):
        out[name] = int(
            await session.scalar(
                select(func.count()).select_from(model).where(model.status == "approved")
            )
            or 0
        )
    return out
