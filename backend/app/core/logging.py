"""Structured JSON logs with request_id, farm_id and user_id bound per request."""

import logging
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.requests import Request
from starlette.responses import Response


def configure_logging(level: int = logging.INFO) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )


def bind(**values: object) -> None:
    structlog.contextvars.bind_contextvars(**values)


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    structlog.contextvars.clear_contextvars()
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    if len(request_id) > 64 or not request_id.isprintable():
        request_id = uuid.uuid4().hex
    bind(request_id=request_id)
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response
