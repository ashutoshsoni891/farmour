"""Caretaker single-use login links (spec sections 2, 12, 14)."""

import re

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import Fakes
from tests.helpers import add_caretaker, auth, owner_with_farm

pytestmark = pytest.mark.integration

PHONE = "+919812345678"


async def _caretaker(client: AsyncClient, fakes: Fakes, session: AsyncSession) -> None:
    _, farm_id = await owner_with_farm(client, fakes)
    await add_caretaker(session, farm_id, phone=PHONE, chat_id="chat-1")


def _token_from(fakes: Fakes) -> str:
    match = re.search(r"#token=([\w-]+)", fakes.channel.sent[-1].text)
    assert match
    return match.group(1)


async def test_link_sent_in_hindi_and_verifies_once(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    await _caretaker(client, fakes, session)
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "98123 45678"})
    assert r.status_code == 202
    msg = fakes.channel.sent[-1]
    assert msg.chat_id == "chat-1"
    assert "फ़ार्म" in msg.text
    assert "https://app.test/login/link#token=" in msg.text

    token = _token_from(fakes)
    r = await client.post("/api/v1/auth/otp/verify", json={"token": token})
    assert r.status_code == 200
    session_token = r.json()["access_token"]
    me = await client.get("/api/v1/me", headers=auth(session_token))
    assert me.status_code == 200
    assert me.json()["phone"] == PHONE

    again = await client.post("/api/v1/auth/otp/verify", json={"token": token})
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "LINK_INVALID"


async def test_unknown_phone_gets_same_response_and_no_message(
    client: AsyncClient, fakes: Fakes
) -> None:
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "9000000001"})
    assert r.status_code == 202
    assert fakes.channel.sent == []


async def test_expired_link_rejected(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    await _caretaker(client, fakes, session)
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    await session.execute(text("update login_links set expires_at = now() - interval '1 minute'"))
    await session.flush()
    r = await client.post("/api/v1/auth/otp/verify", json={"token": _token_from(fakes)})
    assert r.status_code == 401


async def test_rate_limited_after_three_requests(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    await _caretaker(client, fakes, session)
    codes = [
        (await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})).status_code
        for _ in range(4)
    ]
    assert codes == [202, 202, 202, 429]
    assert len(fakes.channel.sent) == 3


async def test_revoking_sessions_invalidates_token(
    client: AsyncClient, fakes: Fakes, session: AsyncSession
) -> None:
    await _caretaker(client, fakes, session)
    await client.post("/api/v1/auth/otp/request", json={"phone": PHONE})
    r = await client.post("/api/v1/auth/otp/verify", json={"token": _token_from(fakes)})
    session_token = r.json()["access_token"]
    await session.execute(
        text("update users set session_version = session_version + 1 where phone = :p"),
        {"p": PHONE},
    )
    await session.flush()
    assert (await client.get("/api/v1/me", headers=auth(session_token))).status_code == 401


async def test_invalid_phone_rejected(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/otp/request", json={"phone": "12345"})
    assert r.status_code == 422
