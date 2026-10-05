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


class CropRef(BaseModel):
    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    ai_checked: bool  # AI-checked library entry, not yet reviewed by an expert


class SeasonOut(BaseModel):
    season: str
    label: str
    begin: date
    end: date


class PlantingOut(BaseModel):
    bed_code: str
    season: str
    season_label: str
    layer: str
    crop: CropRef
    planned_sow: date
    plant_count: int
    spacing_cm: int
    expected_yield_kg: float
    why: dict[str, Any]


class PlanWarning(BaseModel):
    code: str
    message_key: str
    params: dict[str, Any] = {}


class PlanOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    version: int
    status: PlanStatus
    start_date: date
    engine_version: str
    template: str
    area_sqm: float
    warnings: list[PlanWarning]
    zones: list[ZoneOut]
    beds: list[BedOut]
    seasons: list[SeasonOut]
    plantings: list[PlantingOut]
    uses_ai_checked: bool
    created_at: datetime
