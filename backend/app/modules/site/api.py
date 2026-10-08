"""Routes: /farms/{farm_id}/site-profile."""

from fastapi import APIRouter, status

from app.modules.farms.service import Membership, membership
from app.modules.identity.deps import CurrentUser, SessionDep
from app.modules.site import service
from app.modules.site.schemas import AnswerBatch, CostNormOut, KvkOut, MarketCentreOut, ProfileOut

router = APIRouter(prefix="/farms/{farm_id}/site-profile", tags=["site"])


@router.get("")
async def get_profile(session: SessionDep, m: Membership = membership()) -> ProfileOut:
    """Facts found for the land, each with source, date and confidence."""
    return await service.get_profile(session, m)


@router.patch("")
async def answer(
    body: AnswerBatch, session: SessionDep, m: Membership = membership("owner")
) -> ProfileOut:
    """Looks right (confirm), Change (edit) or Not sure (reject). The owner's answer always wins."""
    return await service.answer(session, m, body)


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh(session: SessionDep, m: Membership = membership("owner")) -> None:
    await service.request_refresh(session, m)


catalog_router = APIRouter(prefix="/cost-norms", tags=["site"])


@catalog_router.get("")
async def cost_norms(session: SessionDep, _user: CurrentUser) -> list[CostNormOut]:
    """Setup costs and subsidy rates from the government's cost norms, each with its source."""
    return await service.list_cost_norms(session)


market_router = APIRouter(prefix="/market-centres", tags=["site"])


@market_router.get("")
async def market_centres(session: SessionDep, _user: CurrentUser) -> list[MarketCentreOut]:
    """Herb mandis and portals where crops can be sold or priced, each with its source."""
    return await service.list_market_centres(session)


kvk_router = APIRouter(prefix="/kvks", tags=["site"])


@kvk_router.get("")
async def kvks(
    session: SessionDep, _user: CurrentUser, district: str | None = None
) -> list[KvkOut]:
    """Krishi Vigyan Kendras (government farm advisory centres) with the cited directory entry."""
    return await service.list_kvks(session, district)
