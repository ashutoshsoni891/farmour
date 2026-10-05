"""Routes: /farms/{farm_id}/plan."""

from fastapi import APIRouter

from app.modules.farms.service import Membership, membership
from app.modules.identity.deps import SessionDep
from app.modules.layout import service
from app.modules.layout.schemas import PlanOut

router = APIRouter(prefix="/farms/{farm_id}/plan", tags=["plan"])


@router.get("")
async def get_plan(session: SessionDep, m: Membership = membership()) -> PlanOut:
    """The farm's latest plan (zones and beds as GeoJSON)."""
    return await service.get_plan(session, m)


@router.post("", status_code=201)
async def generate_plan(session: SessionDep, m: Membership = membership("owner")) -> PlanOut:
    """Build a new draft plan from the farm's plot (owner only)."""
    return await service.generate_plan(session, m)
