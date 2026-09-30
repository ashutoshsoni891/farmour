"""Routes: /farms, /farms/{farm_id}, members and invites."""

import uuid

from fastapi import APIRouter, status

from app.modules.farms import service
from app.modules.farms.schemas import (
    FarmCreate,
    FarmOut,
    FarmUpdate,
    InviteCreate,
    InviteOut,
    MemberOut,
    MemberUpdate,
)
from app.modules.farms.service import Membership, membership
from app.modules.identity.service import CurrentUser, SessionDep

router = APIRouter(prefix="/farms", tags=["farms"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_farm(body: FarmCreate, principal: CurrentUser, session: SessionDep) -> FarmOut:
    return await service.create_farm(session, principal, body)


@router.get("")
async def list_farms(principal: CurrentUser, session: SessionDep) -> list[FarmOut]:
    return await service.list_my_farms(session, principal)


@router.get("/{farm_id}")
async def get_farm(session: SessionDep, m: Membership = membership()) -> FarmOut:
    return await service.get_farm(session, m)


@router.patch("/{farm_id}")
async def patch_farm(
    body: FarmUpdate, session: SessionDep, m: Membership = membership("owner")
) -> FarmOut:
    return await service.update_farm(session, m, body)


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_farm(session: SessionDep, m: Membership = membership("owner")) -> None:
    await service.delete_farm(session, m)


@router.get("/{farm_id}/members")
async def list_members(session: SessionDep, m: Membership = membership("owner")) -> list[MemberOut]:
    return await service.list_members(session, m)


@router.patch("/{farm_id}/members/{user_id}")
async def patch_member(
    user_id: uuid.UUID,
    body: MemberUpdate,
    session: SessionDep,
    m: Membership = membership("owner"),
) -> MemberOut:
    return await service.update_member(session, m, user_id, body)


@router.post("/{farm_id}/members/invite", status_code=status.HTTP_201_CREATED)
async def invite(
    body: InviteCreate, session: SessionDep, m: Membership = membership("owner")
) -> InviteOut:
    return await service.invite_caretaker(session, m, body)
