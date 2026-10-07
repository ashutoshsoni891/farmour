"""Mounts every module router under /api/v1 (spec section 12)."""

from fastapi import APIRouter

from app.api import geo, settings
from app.modules.farms.api import router as farms_router
from app.modules.identity.api import router as identity_router
from app.modules.layout.api import router as layout_router
from app.modules.library.api import router as library_router
from app.modules.parcel.api import router as parcel_router
from app.modules.site.api import catalog_router as cost_norms_router
from app.modules.site.api import kvk_router
from app.modules.site.api import router as site_router

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(identity_router)
api_v1.include_router(farms_router)
api_v1.include_router(layout_router)
api_v1.include_router(library_router)
api_v1.include_router(parcel_router)
api_v1.include_router(site_router)
api_v1.include_router(cost_norms_router)
api_v1.include_router(kvk_router)
api_v1.include_router(geo.router)
api_v1.include_router(settings.router)
