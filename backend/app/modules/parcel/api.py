"""Routes: /farms/{farm_id}/parcel."""

from fastapi import APIRouter

from app.modules.farms.service import Membership, membership
from app.modules.identity.deps import SessionDep
from app.modules.parcel import service
from app.modules.parcel.schemas import MeasurementsSave, ParcelOut, ParcelSave

router = APIRouter(prefix="/farms/{farm_id}/parcel", tags=["parcel"])


@router.get("")
async def get_parcel(session: SessionDep, m: Membership = membership()) -> ParcelOut:
    return await service.get_parcel(session, m)


@router.put("")
async def save_parcel(
    body: ParcelSave, session: SessionDep, m: Membership = membership("owner")
) -> ParcelOut:
    """Save the drawn boundary (GeoJSON, WGS84); returns the measured area and perimeter."""
    return await service.save_parcel(session, m, body)


@router.post("/from-measurements")
async def from_measurements(
    body: MeasurementsSave, session: SessionDep, m: Membership = membership("owner")
) -> ParcelOut:
    """Build the plot from a length x width rectangle or four sides plus a diagonal."""
    return await service.save_from_measurements(session, m, body)
