"""Database access for users, channel accounts and login links. Only this module imports it."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import ChannelAccount, LoginLink, User


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))


async def get_by_keycloak_sub(session: AsyncSession, sub: str) -> User | None:
    return await session.scalar(select(User).where(User.keycloak_sub == sub))


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    return await session.scalar(select(User).where(User.phone == phone, User.deleted_at.is_(None)))


async def add_user(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.flush()
    return user


async def list_users(session: AsyncSession, *, after: uuid.UUID | None, limit: int) -> list[User]:
    stmt = select(User).where(User.deleted_at.is_(None)).order_by(User.id).limit(limit)
    if after:
        stmt = stmt.where(User.id > after)
    return list(await session.scalars(stmt))


async def active_channel_account(
    session: AsyncSession, user_id: uuid.UUID
) -> ChannelAccount | None:
    return await session.scalar(
        select(ChannelAccount)
        .where(ChannelAccount.user_id == user_id, ChannelAccount.opted_out.is_(False))
        .order_by(ChannelAccount.created_at.desc())
        .limit(1)
    )


async def add_login_link(session: AsyncSession, link: LoginLink) -> None:
    session.add(link)
    await session.flush()


async def consume_login_link(
    session: AsyncSession, token_hash: str, now: datetime
) -> uuid.UUID | None:
    """Atomically mark an unused, unexpired link as used; return its user id."""
    return await session.scalar(
        update(LoginLink)
        .where(
            LoginLink.token_hash == token_hash,
            LoginLink.used_at.is_(None),
            LoginLink.expires_at > now,
        )
        .values(used_at=now)
        .returning(LoginLink.user_id)
    )


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(
        select(User).where(User.email == email, User.deleted_at.is_(None)).limit(1)
    )
