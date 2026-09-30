"""Public entry point of the identity module: authentication, profile and user admin."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.channel import OutboundMessage, get_channel
from app.adapters.identity import TokenVerifyError, get_token_verifier
from app.config import get_config
from app.core import audit, rate_limit, session_tokens
from app.core.errors import AppError, not_found, unauthenticated
from app.core.i18n import Lang, t
from app.core.settings_store import get_int, get_setting
from app.modules.identity import repository as repo
from app.modules.identity.models import LoginLink, User
from app.modules.identity.schemas import (
    AdminUserUpdate,
    MeUpdate,
    Principal,
    SessionOut,
)

log = structlog.get_logger()


def _principal(user: User) -> Principal:
    return Principal(
        user_id=user.id,
        language=cast(Lang, user.language),
        is_admin=user.is_admin,
        is_agronomist=user.is_agronomist,
    )


async def _user_from_keycloak(session: AsyncSession, token: str) -> User:
    try:
        claims = await get_token_verifier().verify(token)
    except TokenVerifyError:
        raise unauthenticated() from None
    # Only a verified email is stored, so nobody can claim someone else's address.
    email = claims.email if claims.email_verified else None
    user = await repo.get_by_keycloak_sub(session, claims.subject)
    if user is None:
        # First login: provision a local profile. Roles are granted by an admin, not by the token.
        user = await repo.add_user(
            session, User(keycloak_sub=claims.subject, email=email, name=claims.name)
        )
        log.info("identity.user_provisioned", user_id=str(user.id))
    elif user.email != email:
        user.email = email
    if user.deleted_at is not None:
        raise unauthenticated()
    return user


async def _user_from_session_token(session: AsyncSession, token: str) -> User:
    try:
        claims = session_tokens.verify(token)
    except session_tokens.SessionTokenError:
        raise unauthenticated() from None
    user = await repo.get_user(session, claims.user_id)
    if (
        user is None
        or user.session_version != claims.session_version
        or not _link_login_allowed(user)
    ):
        raise unauthenticated()
    return user


def _link_login_allowed(user: User) -> bool:
    """Link login is for caretakers only. Keycloak accounts, admins and agronomists must use
    Keycloak (password/passkey, brute-force protection), never a messaging-app link."""
    return user.keycloak_sub is None and not user.is_admin and not user.is_agronomist


async def authenticate(session: AsyncSession, token: str) -> Principal:
    """Resolve a bearer token to a principal, or raise UNAUTHENTICATED."""
    if session_tokens.is_session_token(token):
        user = await _user_from_session_token(session, token)
    else:
        user = await _user_from_keycloak(session, token)
    return _principal(user)


# ---- profile ----


async def get_me(session: AsyncSession, principal: Principal) -> User:
    user = await repo.get_user(session, principal.user_id)
    if user is None:
        raise not_found("user")
    return user


async def update_me(session: AsyncSession, principal: Principal, data: MeUpdate) -> User:
    user = await get_me(session, principal)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await session.flush()
    return user


# ---- caretaker single-use login links ----


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def request_login_link(session: AsyncSession, phone: str, client_ip: str) -> None:
    """Send a single-use login link to the caretaker's messaging app, if the phone is known.

    The response never reveals whether the phone is registered.
    """
    limit: dict[str, Any] = await get_setting(session, "auth.link_rate_limit")
    window = int(limit["window_minutes"]) * 60
    # IP first, so requests from a blocked IP don't use up the victim's per-phone budget.
    await rate_limit.enforce(
        f"link:ip:{client_ip}", limit=int(limit["max_per_ip"]), window_seconds=window
    )
    await rate_limit.enforce(f"link:phone:{phone}", limit=int(limit["max"]), window_seconds=window)

    user = await repo.get_by_phone(session, phone)
    account = await repo.active_channel_account(session, user.id) if user else None
    if user is None or account is None or not _link_login_allowed(user):
        log.info("identity.link_request_ignored")
        return

    ttl_min = await get_int(session, "auth.link_ttl_minutes")
    token = secrets.token_urlsafe(32)
    await repo.add_login_link(
        session,
        LoginLink(
            user_id=user.id,
            token_hash=_hash(token),
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_min),
        ),
    )
    # Token in the URL fragment so it never reaches server or proxy logs.
    url = f"{get_config().app_base_url.rstrip('/')}/login/link#token={token}"
    text = t("auth.login_link", cast(Lang, user.language), url=url, minutes=ttl_min)
    await get_channel().send(OutboundMessage(chat_id=account.external_id, text=text))


async def verify_login_link(session: AsyncSession, token: str) -> SessionOut:
    user_id = await repo.consume_login_link(session, _hash(token), datetime.now(UTC))
    if user_id is None:
        raise AppError("LINK_INVALID", 401)
    user = await repo.get_user(session, user_id)
    if user is None or not _link_login_allowed(user):
        raise AppError("LINK_INVALID", 401)
    days = await get_int(session, "auth.caretaker_session_days")
    ttl = timedelta(days=days)
    return SessionOut(
        access_token=session_tokens.issue(user.id, user.session_version, ttl),
        expires_in=int(ttl.total_seconds()),
    )


# ---- admin ----


async def list_users(
    session: AsyncSession, *, cursor: uuid.UUID | None, limit: int
) -> tuple[list[User], uuid.UUID | None]:
    users = await repo.list_users(session, after=cursor, limit=limit + 1)
    next_cursor = users[limit - 1].id if len(users) > limit else None
    return users[:limit], next_cursor


async def admin_update_user(
    session: AsyncSession, actor: Principal, user_id: uuid.UUID, data: AdminUserUpdate
) -> User:
    user = await repo.get_user(session, user_id)
    if user is None:
        raise not_found("user")
    before = {"is_admin": user.is_admin, "is_agronomist": user.is_agronomist}
    if data.is_admin is not None:
        if user.id == actor.user_id and not data.is_admin:
            raise AppError("CANNOT_REMOVE_OWN_ADMIN", 409)
        user.is_admin = data.is_admin
    if data.is_agronomist is not None:
        user.is_agronomist = data.is_agronomist
    if data.revoke_sessions:
        user.session_version += 1
    after = {"is_admin": user.is_admin, "is_agronomist": user.is_agronomist}
    await audit.record(
        session,
        actor_id=actor.user_id,
        entity="user",
        entity_id=user.id,
        action="admin_update",
        before=before,
        after=after | {"revoked_sessions": data.revoke_sessions},
    )
    await session.flush()
    return user


# ---- used by other modules ----


async def user_exists(session: AsyncSession, user_id: uuid.UUID) -> bool:
    return await repo.get_user(session, user_id) is not None


async def grant_admin_by_email(session: AsyncSession, email: str) -> str:
    """Bootstrap: make an existing user with this verified email an admin (CLI only).

    Returns "granted", "not_found" or "ambiguous"; ambiguous matches are refused.
    """
    users = await repo.users_with_email(session, email)
    if not users:
        return "not_found"
    if len(users) > 1:
        return "ambiguous"
    user = users[0]
    user.is_admin = True
    await audit.record(
        session, actor_id=None, entity="user", entity_id=user.id, action="grant_admin_cli"
    )
    return "granted"
