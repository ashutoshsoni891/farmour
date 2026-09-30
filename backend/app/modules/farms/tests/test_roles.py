"""Row-level farm authorisation and money visibility (spec sections 2 and 14)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import session_tokens
from tests.fixtures import Fakes
from tests.helpers import add_caretaker, auth, owner_with_farm

pytestmark = pytest.mark.integration


def caretaker_token(user_id: object) -> str:
    from datetime import timedelta
    from uuid import UUID

    return session_tokens.issue(UUID(str(user_id)), 1, timedelta(minutes=5))


OWNER_ONLY = [  # DELETE last: the owner test runs these in order on one farm
    ("PATCH", "", {"name": "x"}),
    ("GET", "/members", None),
    ("POST", "/members/invite", {"phone": "9876543210"}),
    ("DELETE", "", None),
]


async def test_owner_can_do_everything(client: AsyncClient, fakes: Fakes) -> None:
    owner, farm = await owner_with_farm(client, fakes)
    r = await client.get(f"/api/v1/farms/{farm}", headers=auth(owner))
    assert r.status_code == 200
    assert r.json()["my_role"] == "owner"
    assert r.json()["budget_setup_paise"] == 4_200_000
    for method, suffix, body in OWNER_ONLY:
        r = await client.request(
            method, f"/api/v1/farms/{farm}{suffix}", json=body, headers=auth(owner)
        )
        assert r.status_code in (200, 201, 204), (method, suffix, r.text)


@pytest.mark.parametrize(("method", "suffix", "body"), OWNER_ONLY)
async def test_caretaker_cannot_do_owner_actions(
    client: AsyncClient,
    fakes: Fakes,
    session: AsyncSession,
    method: str,
    suffix: str,
    body: dict[str, object] | None,
) -> None:
    _, farm = await owner_with_farm(client, fakes)
    ct = caretaker_token(await add_caretaker(session, farm))
    r = await client.request(method, f"/api/v1/farms/{farm}{suffix}", json=body, headers=auth(ct))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_ROLE"


@pytest.mark.parametrize(("method", "suffix", "body"), [("GET", "", None), *OWNER_ONLY])
async def test_non_member_cannot_see_the_farm_exists(
    client: AsyncClient, fakes: Fakes, method: str, suffix: str, body: dict[str, object] | None
) -> None:
    _, farm = await owner_with_farm(client, fakes)
    other_owner, _ = await owner_with_farm(client, fakes)
    r = await client.request(
        method, f"/api/v1/farms/{farm}{suffix}", json=body, headers=auth(other_owner)
    )
    assert r.status_code == 404


async def test_caretaker_never_sees_money_unless_allowed(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    owner, farm = await owner_with_farm(client, fakes)
    uid = await add_caretaker(session, farm)
    ct = caretaker_token(uid)

    r = await client.get(f"/api/v1/farms/{farm}", headers=auth(ct))
    assert r.status_code == 200
    assert r.json()["my_role"] == "caretaker"
    assert r.json()["budget_setup_paise"] is None
    listed = (await client.get("/api/v1/farms", headers=auth(ct))).json()
    assert listed[0]["budget_setup_paise"] is None

    r = await client.patch(
        f"/api/v1/farms/{farm}/members/{uid}",
        json={"caretaker_sees_money": True},
        headers=auth(owner),
    )
    assert r.status_code == 200
    r = await client.get(f"/api/v1/farms/{farm}", headers=auth(ct))
    assert r.json()["budget_setup_paise"] == 4_200_000


async def test_caretaker_of_one_farm_cannot_read_another(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    _, farm_a = await owner_with_farm(client, fakes)
    _, farm_b = await owner_with_farm(client, fakes)
    ct = caretaker_token(await add_caretaker(session, farm_a))
    assert (await client.get(f"/api/v1/farms/{farm_b}", headers=auth(ct))).status_code == 404


async def test_deleted_farm_is_gone_for_everyone(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    owner, farm = await owner_with_farm(client, fakes)
    assert (await client.delete(f"/api/v1/farms/{farm}", headers=auth(owner))).status_code == 204
    assert (await client.get(f"/api/v1/farms/{farm}", headers=auth(owner))).status_code == 404
    assert (
        await session.scalar(
            text("select count(*) from audit_log where entity='farm' and entity_id=:f"), {"f": farm}
        )
        == 2
    )  # create + soft_delete


async def test_invite_returns_link_and_stores_only_a_hash(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    owner, farm = await owner_with_farm(client, fakes)
    r = await client.post(
        f"/api/v1/farms/{farm}/members/invite", json={"phone": "9876543210"}, headers=auth(owner)
    )
    assert r.status_code == 201
    url = r.json()["invite_url"]
    token = url.split("#token=")[1]
    stored = await session.scalar(
        text("select token_hash from invites where farm_id=:f"), {"f": farm}
    )
    assert stored is not None
    assert token not in stored


async def test_farm_validation(client: AsyncClient, fakes: Fakes) -> None:
    owner = fakes.keycloak_token()
    for body in (
        {"name": ""},
        {"name": "x", "site_type": "roof"},
        {"name": "x", "budget_setup_paise": -1},
        {"name": "x", "lat": 91},
        {"name": "x", "unknown": 1},
    ):
        r = await client.post("/api/v1/farms", json=body, headers=auth(owner))
        assert r.status_code == 422, body
