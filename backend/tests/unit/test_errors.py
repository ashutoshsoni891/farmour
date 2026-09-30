from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import AppError, install_error_handlers


class Body(BaseModel):
    n: int


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise AppError("PARCEL_TOO_SMALL", 422, {"min_sqm": 5})

    @app.post("/validate")
    async def validate(body: Body) -> int:
        return body.n

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("secret internals")

    return app


def test_app_error_uses_spec_format() -> None:
    r = TestClient(_app()).get("/boom")
    assert r.status_code == 422
    assert r.json() == {
        "error": {
            "code": "PARCEL_TOO_SMALL",
            "message_key": "err.parcel_too_small",
            "details": {"min_sqm": 5},
        }
    }


def test_validation_error_format() -> None:
    r = TestClient(_app()).post("/validate", json={"n": "x"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["details"]["fields"][0]["loc"] == ["body", "n"]


def test_not_found_route_format() -> None:
    r = TestClient(_app()).get("/nope")
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_unhandled_error_hides_internals() -> None:
    r = TestClient(_app(), raise_server_exceptions=False).get("/crash")
    assert r.status_code == 500
    assert "secret" not in r.text
    assert r.json()["error"]["code"] == "INTERNAL_ERROR"
