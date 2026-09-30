"""Mounts every module router under /api/v1 (spec section 12)."""

from fastapi import APIRouter

from app.api import settings
from app.modules.farms.api import router as farms_router
from app.modules.identity.api import router as identity_router

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(identity_router)
api_v1.include_router(farms_router)
api_v1.include_router(settings.router)
