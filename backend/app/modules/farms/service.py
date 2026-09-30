"""Public entry point of the farms module: farms, members, invites and access checks."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_config
from app.core import audit
from app.core.errors import AppError, not_found
from app.core.settings_store import get_int
from app.modules.farms import repository as repo
from app.modules.farms.access import Membership, membership, require_farm_role
from app.modules.farms.models import Farm, FarmMember, Invite
from app.modules.farms.schemas import (
    FarmCreate,
    FarmOut,
    FarmUpdate,
    InviteCreate,
    InviteOut,
    MemberOut,
    MemberUpdate,
    Role,
)
from app.modules.identity.schemas import Principal

__all__ = [
    "Membership",
    "create_farm",
    "delete_farm",
    "get_farm",
    "invite_caretaker",
    "list_members",
    "list_my_farms",
    "membership",
    "require_farm_role",
    "update_farm",
    "update_member",
]

MONEY_FIELDS = ("budget_setup_paise", "budget_monthly_paise")


def to_out(farm: Farm, role: Role, can_see_money: bool) -> FarmOut:
    data = {f: getattr(farm, f) for f in FarmOut.model_fields if f != "my_role"}
    if not can_see_money:
        for f in MONEY_FIELDS:
            data[f] = None
    return FarmOut(my_role=role, **data)


def _snapshot(farm: Farm) -> dict[str, object]:
    return {f: _jsonable(getattr(farm, f)) for f in FarmUpdate.model_fields}


def _jsonable(v: object) -> object:
    return str(v) if isinstance(v, (uuid.UUID, datetime)) or type(v).__name__ == "Decimal" else v


async def create_farm(session: AsyncSession, principal: Principal, data: FarmCreate) -> FarmOut:
    fields = data.model_dump(exclude_none=True)
    farm = Farm(id=uuid.uuid4(), created_by=principal.user_id, **fields)
    member = FarmMember(farm_id=farm.id, user_id=principal.user_id, role="owner")
    await repo.add(session, farm)
    await repo.add(session, member)
    await audit.record(
        session,
        actor_id=principal.user_id,
        entity="farm",
        entity_id=farm.id,
        action="create",
        after=_snapshot(farm),
    )
    await session.refresh(farm)
    return to_out(farm, "owner", True)


async def list_my_farms(session: AsyncSession, principal: Principal) -> list[FarmOut]:
    out = []
    for farm, m in await repo.farms_for_user(session, principal.user_id):
        role: Role = "owner" if m.role == "owner" else "caretaker"
        out.append(to_out(farm, role, role == "owner" or m.caretaker_sees_money))
    return out


async def _farm(session: AsyncSession, farm_id: uuid.UUID) -> Farm:
    farm = await repo.get_farm(session, farm_id)
    if farm is None:
        raise not_found("farm")
    return farm


async def get_farm(session: AsyncSession, m: Membership) -> FarmOut:
    return to_out(await _farm(session, m.farm_id), m.role, m.can_see_money)


async def update_farm(session: AsyncSession, m: Membership, data: FarmUpdate) -> FarmOut:
    farm = await _farm(session, m.farm_id)
    before = _snapshot(farm)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "name" and value is None:
            continue
        setattr(farm, field, value)
    await session.flush()
    await audit.record(
        session,
        actor_id=m.user_id,
        entity="farm",
        entity_id=farm.id,
        action="update",
        before=before,
        after=_snapshot(farm),
    )
    await session.refresh(farm)
    return to_out(farm, m.role, m.can_see_money)


async def delete_farm(session: AsyncSession, m: Membership) -> None:
    farm = await _farm(session, m.farm_id)
    farm.deleted_at = datetime.now(UTC)
    await audit.record(
        session, actor_id=m.user_id, entity="farm", entity_id=farm.id, action="soft_delete"
    )


async def list_members(session: AsyncSession, m: Membership) -> list[MemberOut]:
    return [MemberOut.model_validate(x) for x in await repo.list_members(session, m.farm_id)]


async def update_member(
    session: AsyncSession, m: Membership, user_id: uuid.UUID, data: MemberUpdate
) -> MemberOut:
    member = await repo.get_membership(session, m.farm_id, user_id)
    if member is None:
        raise not_found("member")
    if member.role != "caretaker":
        raise AppError("NOT_A_CARETAKER", 409)
    before = {"caretaker_sees_money": member.caretaker_sees_money}
    member.caretaker_sees_money = data.caretaker_sees_money
    await audit.record(
        session,
        actor_id=m.user_id,
        entity="farm_member",
        entity_id=f"{m.farm_id}:{user_id}",
        action="update",
        before=before,
        after={"caretaker_sees_money": data.caretaker_sees_money},
    )
    await session.flush()
    return MemberOut.model_validate(member)


async def invite_caretaker(session: AsyncSession, m: Membership, data: InviteCreate) -> InviteOut:
    """Create an invite link the owner can share. Messaging-app delivery and acceptance
    (binding the caretaker's Telegram account) arrive with the Telegram milestone (M5)."""
    ttl_days = await get_int(session, "invites.ttl_days")
    token = secrets.token_urlsafe(32)
    invite = Invite(
        id=uuid.uuid4(),
        farm_id=m.farm_id,
        phone=data.phone,
        role=data.role,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=ttl_days),
        created_by=m.user_id,
    )
    await repo.add(session, invite)
    await audit.record(
        session,
        actor_id=m.user_id,
        entity="invite",
        entity_id=invite.id,
        action="create",
        after={"farm_id": str(m.farm_id), "role": data.role},
    )
    url = f"{get_config().app_base_url.rstrip('/')}/invite#token={token}"
    return InviteOut(
        id=invite.id,
        phone=invite.phone,
        role=data.role,
        expires_at=invite.expires_at,
        invite_url=url,
    )
