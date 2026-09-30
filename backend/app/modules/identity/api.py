"""Routes: /auth (caretaker links), /me, /admin/users."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.modules.identity import service
from app.modules.identity.schemas import (
    AdminUserOut,
    AdminUserUpdate,
    LinkRequest,
    LinkRequestAccepted,
    LinkVerify,
    MeOut,
    MeUpdate,
    SessionOut,
    UserPage,
)
from app.modules.identity.service import AdminUser, CurrentUser, SessionDep

router = APIRouter()


@router.post("/auth/otp/request", status_code=status.HTTP_202_ACCEPTED, tags=["auth"])
async def request_link(
    body: LinkRequest, request: Request, session: SessionDep
) -> LinkRequestAccepted:
    """Send a caretaker a single-use login link in their messaging app."""
    await service.request_login_link(session, body.phone, request)
    return LinkRequestAccepted()


@router.post("/auth/otp/verify", tags=["auth"])
async def verify_link(body: LinkVerify, session: SessionDep) -> SessionOut:
    return await service.verify_login_link(session, body.token)


@router.get("/me", tags=["me"])
async def get_me(principal: CurrentUser, session: SessionDep) -> MeOut:
    return MeOut.model_validate(await service.get_me(session, principal))


@router.patch("/me", tags=["me"])
async def patch_me(body: MeUpdate, principal: CurrentUser, session: SessionDep) -> MeOut:
    return MeOut.model_validate(await service.update_me(session, principal, body))


@router.get("/admin/users", tags=["admin"])
async def admin_list_users(
    _: AdminUser,
    session: SessionDep,
    cursor: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserPage:
    users, next_cursor = await service.list_users(session, cursor=cursor, limit=limit)
    return UserPage(items=[AdminUserOut.model_validate(u) for u in users], next_cursor=next_cursor)


@router.patch("/admin/users/{user_id}", tags=["admin"])
async def admin_patch_user(
    user_id: uuid.UUID, body: AdminUserUpdate, actor: AdminUser, session: SessionDep
) -> AdminUserOut:
    user = await service.admin_update_user(session, actor, user_id, body)
    return AdminUserOut.model_validate(user)
