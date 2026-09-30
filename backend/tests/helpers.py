"""Helpers to create users and memberships directly (test setup only)."""

import uuid

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import Fakes


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def owner_with_farm(client: AsyncClient, fakes: Fakes, **farm: object) -> tuple[str, str]:
    """Return (owner token, farm id) for a new owner who created a farm."""
    token = fakes.keycloak_token()
    body = {"name": "Test farm", "budget_setup_paise": 4_200_000, **farm}
    r = await client.post("/api/v1/farms", json=body, headers=auth(token))
    assert r.status_code == 201, r.text
    return token, r.json()["id"]


async def user_id_for(client: AsyncClient, token: str) -> str:
    r = await client.get("/api/v1/me", headers=auth(token))
    assert r.status_code == 200, r.text
    return str(r.json()["id"])


async def add_caretaker(
    session: AsyncSession,
    farm_id: str,
    *,
    phone: str | None = None,
    sees_money: bool = False,
    chat_id: str | None = None,
    language: str = "hi",
) -> uuid.UUID:
    uid = uuid.uuid4()
    await session.execute(
        text("insert into users (id, phone, language) values (:id, :phone, :lang)"),
        {"id": uid, "phone": phone, "lang": language},
    )
    await session.execute(
        text(
            "insert into farm_members (farm_id, user_id, role, caretaker_sees_money) "
            "values (:f, :u, 'caretaker', :m)"
        ),
        {"f": farm_id, "u": uid, "m": sees_money},
    )
    if chat_id:
        await session.execute(
            text(
                "insert into channel_accounts (id, user_id, channel, external_id) "
                "values (:id, :u, 'fake', :c)"
            ),
            {"id": uuid.uuid4(), "u": uid, "c": chat_id},
        )
    await session.flush()
    return uid


async def make_admin(session: AsyncSession, user_id: str) -> None:
    await session.execute(text("update users set is_admin = true where id = :id"), {"id": user_id})
    await session.flush()
