"""Row-level farm authorisation: the single `require_farm_role` dependency (spec section 14).

Every farm-scoped route depends on it. Non-members get 404 (the farm's existence is not
revealed); members without a permitted role get 403 FORBIDDEN_ROLE.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends

from app.core.errors import forbidden_role, not_found
from app.core.logging import bind
from app.modules.farms import repository as repo
from app.modules.identity.service import CurrentUser, SessionDep

Role = Literal["owner", "caretaker"]


@dataclass(frozen=True)
class Membership:
    farm_id: uuid.UUID
    user_id: uuid.UUID
    role: Role
    can_see_money: bool

    @property
    def is_owner(self) -> bool:
        return self.role == "owner"


def require_farm_role(*roles: Role) -> Callable[..., Awaitable[Membership]]:
    """Dependency factory: `Depends(require_farm_role("owner"))`. No roles = any member."""
    allowed = set(roles) or {"owner", "caretaker"}

    async def dependency(
        farm_id: uuid.UUID, principal: CurrentUser, session: SessionDep
    ) -> Membership:
        member = await repo.get_membership(session, farm_id, principal.user_id)
        if member is None:
            raise not_found("farm")
        bind(farm_id=str(farm_id))
        if member.role not in allowed:
            raise forbidden_role()
        role: Role = "owner" if member.role == "owner" else "caretaker"
        return Membership(
            farm_id=farm_id,
            user_id=principal.user_id,
            role=role,
            can_see_money=role == "owner" or member.caretaker_sees_money,
        )

    return dependency


def membership(*roles: Role) -> Membership:
    """Shorthand for route signatures: `m: Membership = membership("owner")`."""
    result: Membership = Depends(require_farm_role(*roles))
    return result
