"""Database access for farms, members and invites. Only this module imports it."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.farms.models import Farm, FarmMember, Invite


async def get_farm(session: AsyncSession, farm_id: uuid.UUID) -> Farm | None:
    return await session.scalar(select(Farm).where(Farm.id == farm_id, Farm.deleted_at.is_(None)))


async def get_membership(
    session: AsyncSession, farm_id: uuid.UUID, user_id: uuid.UUID
) -> FarmMember | None:
    return await session.scalar(
        select(FarmMember)
        .join(Farm, Farm.id == FarmMember.farm_id)
        .where(
            FarmMember.farm_id == farm_id,
            FarmMember.user_id == user_id,
            Farm.deleted_at.is_(None),
        )
    )


async def farms_for_user(
    session: AsyncSession, user_id: uuid.UUID
) -> list[tuple[Farm, FarmMember]]:
    rows = await session.execute(
        select(Farm, FarmMember)
        .join(FarmMember, FarmMember.farm_id == Farm.id)
        .where(FarmMember.user_id == user_id, Farm.deleted_at.is_(None))
        .order_by(Farm.created_at.desc())
    )
    return [(f, m) for f, m in rows.tuples()]


async def list_members(session: AsyncSession, farm_id: uuid.UUID) -> list[FarmMember]:
    return list(
        await session.scalars(
            select(FarmMember).where(FarmMember.farm_id == farm_id).order_by(FarmMember.created_at)
        )
    )


async def add(session: AsyncSession, *objs: Farm | FarmMember | Invite) -> None:
    session.add_all(objs)
    await session.flush()
