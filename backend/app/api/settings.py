"""Admin routes for the `settings` table (spec section 12: /admin/settings)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core import audit, settings_store
from app.core.errors import not_found
from app.modules.identity.service import AdminUser, SessionDep

router = APIRouter(prefix="/admin/settings", tags=["admin"])


class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    value: Any
    description: str | None


class SettingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Any


@router.get("")
async def list_settings(_: AdminUser, session: SessionDep) -> list[SettingOut]:
    return [SettingOut.model_validate(s) for s in await settings_store.list_settings(session)]


@router.patch("/{key}")
async def update_setting(
    key: str, body: SettingUpdate, actor: AdminUser, session: SessionDep
) -> SettingOut:
    row = await settings_store.get_row(session, key)
    if row is None:
        raise not_found("setting")
    before = {"value": row.value}
    row.value = body.value
    row.updated_by = actor.user_id
    await audit.record(
        session,
        actor_id=actor.user_id,
        entity="setting",
        entity_id=key,
        action="update",
        before=before,
        after={"value": body.value},
    )
    await session.flush()
    settings_store.clear_cache()
    return SettingOut.model_validate(row)
