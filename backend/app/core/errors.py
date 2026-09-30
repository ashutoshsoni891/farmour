"""Error format from spec section 12: {"error": {"code", "message_key", "details"}}.

Handlers never return raw user-facing text; the frontend maps `message_key` to en/hi.
"""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, code: str, status: int = 400, details: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.details = details or {}

    @property
    def message_key(self) -> str:
        return "err." + self.code.lower()


def error_body(code: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message_key": "err." + code.lower(), "details": details or {}}}


# Common errors
def not_found(entity: str) -> AppError:
    return AppError("NOT_FOUND", 404, {"entity": entity})


def forbidden_role() -> AppError:
    return AppError("FORBIDDEN_ROLE", 403)


def unauthenticated() -> AppError:
    return AppError("UNAUTHENTICATED", 401)


_STATUS_CODES = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN_ROLE",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"loc": [str(p) for p in e.get("loc", [])], "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(error_body("VALIDATION_ERROR", {"fields": fields}), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(error_body(code), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        structlog.get_logger().error("unhandled_error", exc_info=exc)
        return JSONResponse(error_body("INTERNAL_ERROR"), status_code=500)
