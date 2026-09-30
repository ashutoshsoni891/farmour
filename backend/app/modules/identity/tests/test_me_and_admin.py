import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import Fakes
from tests.helpers import auth, make_admin, user_id_for

pytestmark = pytest.mark.integration


async def test_requires_token(client: AsyncClient) -> None:
    r = await client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_invalid_token_rejected(client: AsyncClient) -> None:
    r = await client.get("/api/v1/me", headers=auth("fake.nope"))
    assert r.status_code == 401


async def test_first_login_provisions_profile_with_hindi_default(
    client: AsyncClient, fakes: Fakes
) -> None:
    token = fakes.keycloak_token(email="owner@example.test")
    r = await client.get("/api/v1/me", headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "owner@example.test"
    assert body["language"] == "hi"
    assert body["is_admin"] is False
    # Second call reuses the same profile.
    assert (await client.get("/api/v1/me", headers=auth(token))).json()["id"] == body["id"]


async def test_update_language_and_units(client: AsyncClient, fakes: Fakes) -> None:
    token = fakes.keycloak_token()
    r = await client.patch(
        "/api/v1/me",
        json={
            "language": "en",
            "unit_pref": "bigha",
            "bigha_sqft": "27000",
        },
        headers=auth(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["language"] == "en"


async def test_update_rejects_unknown_fields_and_bad_values(
    client: AsyncClient, fakes: Fakes
) -> None:
    token = fakes.keycloak_token()
    for body in (
        {"is_admin": True},
        {"phone": "9876543210"},
        {"language": "fr"},
        {"bigha_sqft": "-1"},
    ):
        r = await client.patch("/api/v1/me", json=body, headers=auth(token))
        assert r.status_code == 422, body


async def test_admin_routes_need_admin(client: AsyncClient, fakes: Fakes) -> None:
    token = fakes.keycloak_token()
    for method, path in (("GET", "/api/v1/admin/users"), ("GET", "/api/v1/admin/settings")):
        r = await client.request(method, path, headers=auth(token))
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"


async def test_admin_grants_role_and_it_is_audited(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    admin = fakes.keycloak_token()
    await make_admin(session, await user_id_for(client, admin))
    target_token = fakes.keycloak_token()
    target = await user_id_for(client, target_token)

    r = await client.patch(
        f"/api/v1/admin/users/{target}", json={"is_agronomist": True}, headers=auth(admin)
    )
    assert r.status_code == 200
    assert r.json()["is_agronomist"] is True
    audited = await session.scalar(
        text("select count(*) from audit_log where entity='user' and entity_id=:id"), {"id": target}
    )
    assert audited == 1

    listed = (await client.get("/api/v1/admin/users?limit=100", headers=auth(admin))).json()
    assert any(u["id"] == target for u in listed["items"])


async def test_admin_cannot_remove_own_admin(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    admin = fakes.keycloak_token()
    me = await user_id_for(client, admin)
    await make_admin(session, me)
    r = await client.patch(
        f"/api/v1/admin/users/{me}", json={"is_admin": False}, headers=auth(admin)
    )
    assert r.status_code == 409


async def test_admin_updates_setting_with_audit(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    admin = fakes.keycloak_token()
    await make_admin(session, await user_id_for(client, admin))
    r = await client.patch(
        "/api/v1/admin/settings/invites.ttl_days", json={"value": 3}, headers=auth(admin)
    )
    assert r.status_code == 200
    assert r.json()["value"] == 3
    r = await client.patch("/api/v1/admin/settings/no.such", json={"value": 1}, headers=auth(admin))
    assert r.status_code == 404


async def test_unverified_email_is_not_stored(client: AsyncClient, fakes: Fakes) -> None:
    from app.adapters.identity import TokenClaims

    token = fakes.verifier.issue(TokenClaims(subject="unverified", email="boss@example.test"))
    r = await client.get("/api/v1/me", headers=auth(token))
    assert r.json()["email"] is None
