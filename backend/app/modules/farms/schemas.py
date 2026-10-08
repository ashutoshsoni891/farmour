import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalise_indian_phone

SiteType = Literal["ground", "terrace"]
Goal = Literal["home_food", "income", "both", "low_work"]
Method = Literal[
    "multilayer", "orchard", "flowers", "natural", "polyhouse", "integrated", "medicinal"
]
BudgetBand = Literal["low", "medium", "high"]
Labour = Literal["self", "family", "caretaker", "mixed"]
WaterSource = Literal["bore", "well", "canal", "municipal", "rain_only"]
Role = Literal["owner", "caretaker"]


class FarmFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_type: SiteType | None = None
    district: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=100)
    lat: Decimal | None = Field(default=None, ge=-90, le=90, decimal_places=6)
    lng: Decimal | None = Field(default=None, ge=-180, le=180, decimal_places=6)
    goal: Goal | None = None
    budget_setup_paise: int | None = Field(default=None, ge=0)
    budget_monthly_paise: int | None = Field(default=None, ge=0)
    labour: Labour | None = None
    water_source: WaterSource | None = None
    water_summer_lpd: int | None = Field(default=None, ge=0)
    electricity: bool | None = None
    livestock: bool | None = None
    methods: list[Method] | None = None
    budget_band: BudgetBand | None = None


class FarmCreate(FarmFields):
    name: str = Field(min_length=1, max_length=200)


class FarmUpdate(FarmFields):
    name: str | None = Field(default=None, min_length=1, max_length=200)


class FarmOut(BaseModel):
    """Money fields are null for caretakers without money access."""

    id: uuid.UUID
    name: str
    my_role: Role
    site_type: SiteType | None
    district: str | None
    village: str | None
    lat: Decimal | None
    lng: Decimal | None
    goal: Goal | None
    budget_setup_paise: int | None
    budget_monthly_paise: int | None
    labour: Labour | None
    water_source: WaterSource | None
    water_summer_lpd: int | None
    electricity: bool | None
    livestock: bool
    methods: list[Method] = []
    budget_band: BudgetBand | None = None
    created_at: datetime


class InviteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone: str
    role: Literal["caretaker"] = "caretaker"

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalise_indian_phone(v)


class InviteOut(BaseModel):
    id: uuid.UUID
    phone: str
    role: Literal["caretaker"]
    expires_at: datetime
    invite_url: str


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    role: Role
    caretaker_sees_money: bool


class MemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caretaker_sees_money: bool
