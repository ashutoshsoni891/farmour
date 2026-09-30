import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalise_indian_phone

Language = Literal["en", "hi"]
UnitPref = Literal["sqft", "acre", "bigha", "sqm"]


class Principal(BaseModel):
    """The authenticated caller, available to every route."""

    model_config = ConfigDict(frozen=True)
    user_id: uuid.UUID
    language: Language
    is_admin: bool
    is_agronomist: bool


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    phone: str | None
    name: str | None
    email: str | None
    language: Language
    unit_pref: UnitPref
    bigha_sqft: Decimal | None
    is_admin: bool
    is_agronomist: bool


class MeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=200)
    phone: str | None = None
    language: Language | None = None
    unit_pref: UnitPref | None = None
    bigha_sqft: Decimal | None = Field(default=None, gt=0, le=1_000_000)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        return normalise_indian_phone(v) if v is not None else None


class LinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalise_indian_phone(v)


class LinkRequestAccepted(BaseModel):
    status: Literal["sent_if_registered"] = "sent_if_registered"


class LinkVerify(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=20, max_length=200)


class SessionOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int


class AdminUserOut(MeOut):
    pass


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_admin: bool | None = None
    is_agronomist: bool | None = None
    revoke_sessions: bool = False


class UserPage(BaseModel):
    items: list[AdminUserOut]
    next_cursor: uuid.UUID | None
