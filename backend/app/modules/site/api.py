"""Routes: /farms/{farm_id}/site-profile."""

from fastapi import APIRouter, status

from app.modules.farms.service import Membership, membership
from app.modules.identity.deps import SessionDep
from app.modules.site import service
from app.modules.site.schemas import AnswerBatch, ProfileOut

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
