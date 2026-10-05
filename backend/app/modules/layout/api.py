"""Routes: /farms/{farm_id}/plan (plan options, the chosen plan, and the owner's changes)."""

import uuid

from fastapi import APIRouter

from app.modules.farms.service import Membership, membership
from app.modules.identity.deps import SessionDep
from app.modules.layout import service
from app.modules.layout.schemas import (
    AdjustIn,
    AlternativeOut,
    OptionsOut,
    PlanOut,
    SwapIn,
)

router = APIRouter(prefix="/farms/{farm_id}/plan", tags=["plan"])


@router.get("")
async def get_plan(
    session: SessionDep, m: Membership = membership(), plan_id: uuid.UUID | None = None
) -> PlanOut:
    """A plan by id; else the active plan; else the recommended option of the latest build."""
    return await service.get_plan(session, m, plan_id)


@router.get("/options")
async def list_options(session: SessionDep, m: Membership = membership()) -> OptionsOut:
    """The plan options built side by side, with comparison figures."""
    return await service.list_options(session, m)


@router.post("/options", status_code=201)
async def build_options(session: SessionDep, m: Membership = membership("owner")) -> OptionsOut:
    """Build every plan option for the farm's plot (owner only)."""
    return await service.build_options(session, m)


@router.post("/{plan_id}/adjust", status_code=201)
async def adjust(
    plan_id: uuid.UUID, body: AdjustIn, session: SessionDep, m: Membership = membership("owner")
) -> PlanOut:
    """Re-run an option with the owner's land-use changes and bed size (a new draft)."""
    return await service.adjust(session, m, plan_id, body)


@router.post("/{plan_id}/lock")
async def lock(
    plan_id: uuid.UUID, session: SessionDep, m: Membership = membership("owner")
) -> PlanOut:
    """Make this plan the farm's active plan."""
    return await service.lock(session, m, plan_id)


@router.get("/{plan_id}/beds/{code}/alternatives")
async def alternatives(
    plan_id: uuid.UUID,
    code: str,
    season_label: str,
    layer: str,
    session: SessionDep,
    m: Membership = membership("owner"),
) -> list[AlternativeOut]:
    """Crops that could go in this bed layer and season instead (every rule checked)."""
    return await service.alternatives(session, m, plan_id, code, season_label, layer)


@router.put("/{plan_id}/beds/{code}/layers")
async def swap(
    plan_id: uuid.UUID,
    code: str,
    body: SwapIn,
    session: SessionDep,
    m: Membership = membership("owner"),
) -> PlanOut:
    """Put the owner's chosen crop in a bed layer."""
    return await service.swap(session, m, plan_id, code, body)
