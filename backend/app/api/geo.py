"""Place search for the setup wizard. The browser never calls Nominatim itself: the API proxies
it, so the usage policy (identifying agent, 1 request/second, caching) is enforced in one place."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.adapters.geocode import get_geocoder
from app.core.errors import AppError
from app.core.rate_limit import enforce
from app.modules.identity.deps import CurrentUser

router = APIRouter(prefix="/geo", tags=["geo"])


class PlaceOut(BaseModel):
    name: str
    lat: float
    lng: float
    village: str | None
    district: str | None
    state: str | None


async def _guard(principal: CurrentUser) -> None:
    await enforce(f"geo:{principal.user_id}", limit=30, window_seconds=60)


@router.get("/search")
async def search(
    principal: CurrentUser,
    q: Annotated[str, Query(min_length=2, max_length=120)],
    lang: Literal["en", "hi"] = "en",
) -> list[PlaceOut]:
    await _guard(principal)
    try:
        places = await get_geocoder().search(q, lang=lang, limit=6)
    except Exception as exc:
        raise AppError("GEOCODER_UNAVAILABLE", 503) from exc
    return [PlaceOut(**p.__dict__) for p in places]


@router.get("/reverse")
async def reverse(
    principal: CurrentUser,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    lang: Literal["en", "hi"] = "en",
) -> PlaceOut | None:
    await _guard(principal)
    try:
        place = await get_geocoder().reverse(lat, lng, lang=lang)
    except Exception as exc:
        raise AppError("GEOCODER_UNAVAILABLE", 503) from exc
    return PlaceOut(**place.__dict__) if place else None
