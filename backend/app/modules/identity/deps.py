"""FastAPI dependencies of the identity module: who is calling.

Other modules' routes import `CurrentUser`, `AdminUser` and `SessionDep` from here.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import forbidden_role, unauthenticated
from app.core.logging import bind
from app.db.session import get_session
from app.modules.identity import service
from app.modules.identity.schemas import Principal

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def current_user(
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    """The authenticated caller (Keycloak access token or caretaker session token)."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise unauthenticated()
    principal = await service.authenticate(session, creds.credentials)
    bind(user_id=str(principal.user_id))
    return principal


CurrentUser = Annotated[Principal, Depends(current_user)]


async def require_admin(principal: CurrentUser) -> Principal:
    if not principal.is_admin:
        raise forbidden_role()
    return principal


AdminUser = Annotated[Principal, Depends(require_admin)]


async def require_agronomist(principal: CurrentUser) -> Principal:
    if not principal.is_agronomist:
        raise forbidden_role()
    return principal


AgronomistUser = Annotated[Principal, Depends(require_agronomist)]
