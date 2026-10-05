"""Pydantic contracts for the layout module."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel

PlanStatus = Literal["draft", "active", "archived"]


class ZoneOut(BaseModel):
    id: uuid.UUID
    kind: str
    label: str | None
    area_sqm: float
    geometry: dict[str, Any]


class BedOut(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    code: str
    length_m: float
    width_m: float
    raised: bool
    has_trellis: bool
    orientation_deg: float
    geometry: dict[str, Any]


class Warning_(BaseModel):
    code: str
    message_key: str


class PlanOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    version: int
    status: PlanStatus
    start_date: date
    engine_version: str
    template: str
    area_sqm: float
    warnings: list[Warning_]
    zones: list[ZoneOut]
    beds: list[BedOut]
    created_at: datetime
