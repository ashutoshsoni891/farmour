import contextlib

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.adapters.cache import get_cache
from app.db.session import get_sessionmaker

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, bool]:
    checks = {"database": False, "cache": False}
    # Readiness reports failures instead of raising.
    with contextlib.suppress(Exception):
        async with get_sessionmaker()() as session:
            checks["database"] = (await session.scalar(text("select 1"))) == 1
    with contextlib.suppress(Exception):
        checks["cache"] = await get_cache().ping()
    if not all(checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
