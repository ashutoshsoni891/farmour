"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.api.router import api_v1
from app.config import get_config
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, request_context_middleware


def create_app() -> FastAPI:
    cfg = get_config()
    configure_logging()
    app = FastAPI(
        title="Farm platform API",
        version="1.0.0",
        docs_url="/api/docs" if cfg.env in ("local", "test") else None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    app.middleware("http")(request_context_middleware)
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_v1)
    return app


app = create_app()
