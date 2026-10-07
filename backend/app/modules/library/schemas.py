"""Pydantic v2 contracts for the library module."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

Status = Literal["draft", "ai_verified", "in_review", "approved", "retired"]
Category = Literal[
    "vegetable", "leafy", "root", "spice", "fruit_tree", "fruit_short", "pulse", "cereal",
    "millet", "oilseed", "herb", "border", "green_manure", "flower",
]  # fmt: skip
Layer = Literal["underground", "surface", "middle", "climber", "canopy"]
Season = Literal["kharif", "rabi", "zaid", "perennial"]
Sun = Literal["full", "partial", "shade_tolerant"]
WaterNeed = Literal["low", "medium", "high"]
SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"
MMDD = r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$"


class Source(BaseModel):
    """Where a value came from: a public document (url) or an agronomist's own judgement."""

    model_config = ConfigDict(extra="forbid")
    url: HttpUrl | None = None
    title: str = Field(min_length=1, max_length=300)
    note: str | None = Field(default=None, max_length=1000)
    # Set by the AI research pass: the sentence in the source that states the value, and the day a
    # second pass opened the source and found it. Both present = the value is "ai_verified".
    quote: str | None = Field(default=None, max_length=1000)
    checked_on: date | None = None


Sources = dict[str, list[Source]]


class SowWindow(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    from_: str = Field(alias="from", pattern=MMDD)
    to: str = Field(pattern=MMDD)
    method: Literal["direct", "transplant"]


class RegionalData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sow_windows: list[SowWindow] = []
    agmarknet_commodity: list[str] = []
    price_mandi_paise_per_kg: int | None = Field(default=None, ge=0)
    price_direct_paise_per_kg: int | None = Field(default=None, ge=0)
    price_updated_on: date | None = None
    sources: Sources = {}


class CropFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_en: str | None = Field(default=None, min_length=1, max_length=100)
    name_hi: str | None = Field(default=None, min_length=1, max_length=100)
    scientific_name: str | None = Field(default=None, max_length=150)
    family: str | None = Field(default=None, max_length=40)
    category: Category | None = None
    layers: list[Layer] | None = None
    seasons: list[Season] | None = None
    nursery_days: int | None = Field(default=None, ge=0, le=365)
    days_to_first_harvest: int | None = Field(default=None, ge=1, le=3650)
    harvest_span_days: int | None = Field(default=None, ge=1, le=3650)
    spacing_row_cm: int | None = Field(default=None, ge=1, le=2000)
    spacing_plant_cm: int | None = Field(default=None, ge=1, le=2000)
    rows_per_1_2m_bed: int | None = Field(default=None, ge=1, le=20)
    height_max_cm: int | None = Field(default=None, ge=1, le=5000)
    root_depth_cm: int | None = Field(default=None, ge=1, le=1000)
    sun: Sun | None = None
    water_need: WaterNeed | None = None
    water_l_per_sqm_day: dict[str, float] | None = None
    kc: dict[str, float] | None = None  # crop coefficient by stage: ini, mid, end (FAO-56)
    heat_tolerance_c: int | None = Field(default=None, ge=0, le=60)
    cold_tolerance_c: int | None = Field(default=None, ge=-20, le=40)
    waterlogging_tolerant: bool | None = None
    terrace_ok: bool | None = None
    min_container_depth_cm: int | None = Field(default=None, ge=1, le=300)
    expected_yield_kg_per_sqm: Decimal | None = Field(default=None, ge=0, le=100)
    unit_to_kg: dict[str, float] | None = None
    years_to_bear: Decimal | None = Field(default=None, ge=0, le=50)
    lifespan_years: int | None = Field(default=None, ge=1, le=200)
    tree_spacing_m: Decimal | None = Field(default=None, gt=0, le=50)
    canopy_diameter_m: Decimal | None = Field(default=None, gt=0, le=50)
    low_care: bool | None = None
    regional: dict[str, RegionalData] | None = None  # keyed by region slug
    sources: Sources | None = None
    source_notes: str | None = Field(default=None, max_length=5000)
    todo: list[str] | None = None


class CropCreate(CropFields):
    slug: str = Field(pattern=SLUG, max_length=60)
    name_en: str = Field(min_length=1, max_length=100)
    name_hi: str = Field(min_length=1, max_length=100)
    category: Category


class CropUpdate(CropFields):
    pass


class ReviewInfo(BaseModel):
    status: Status
    revision: int
    submitted_by: uuid.UUID | None
    submitted_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    updated_at: datetime
    missing_for_review: list[str] = []  # why it can't be submitted yet


class CropOut(ReviewInfo):
    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    scientific_name: str | None
    family: str | None
    category: Category
    layers: list[Layer]
    seasons: list[Season]
    nursery_days: int | None
    days_to_first_harvest: int | None
    harvest_span_days: int | None
    spacing_row_cm: int | None
    spacing_plant_cm: int | None
    rows_per_1_2m_bed: int | None
    height_max_cm: int | None
    root_depth_cm: int | None
    sun: Sun | None
    water_need: WaterNeed | None
    water_l_per_sqm_day: dict[str, float] | None
    kc: dict[str, float] | None
    heat_tolerance_c: int | None
    cold_tolerance_c: int | None
    waterlogging_tolerant: bool | None
    terrace_ok: bool | None
    min_container_depth_cm: int | None
    expected_yield_kg_per_sqm: Decimal | None
    unit_to_kg: dict[str, float] | None
    years_to_bear: Decimal | None
    lifespan_years: int | None
    tree_spacing_m: Decimal | None
    canopy_diameter_m: Decimal | None
    low_care: bool | None
    regional: dict[str, RegionalData]
    sources: dict[str, Any]
    source_notes: str | None
    todo: list[str]


class CropSummary(BaseModel):
    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    category: Category
    layers: list[Layer]
    status: Status
    revision: int
    todo_count: int
    updated_at: datetime


class Ingredient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_en: str
    name_hi: str | None = None
    qty: float | None = Field(default=None, ge=0)
    unit: str | None = None


class RecipeFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_en: str | None = Field(default=None, min_length=1, max_length=100)
    name_hi: str | None = Field(default=None, min_length=1, max_length=100)
    ingredients: list[Ingredient] | None = None
    per_area_sqm: Decimal | None = Field(default=None, gt=0)
    steps_en: list[str] | None = None
    steps_hi: list[str] | None = None
    ferment_days: int | None = Field(default=None, ge=0, le=365)
    shelf_life_days: int | None = Field(default=None, ge=0, le=3650)
    apply_every_days: int | None = Field(default=None, ge=1, le=365)
    apply_method: str | None = Field(default=None, max_length=30)
    safety_notes_en: str | None = None
    safety_notes_hi: str | None = None
    sources: Sources | None = None
    source_notes: str | None = None
    todo: list[str] | None = None


class RecipeCreate(RecipeFields):
    slug: str = Field(pattern=SLUG, max_length=60)
    name_en: str = Field(min_length=1, max_length=100)
    name_hi: str = Field(min_length=1, max_length=100)


class RecipeOut(ReviewInfo):
    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    ingredients: list[Ingredient]
    per_area_sqm: Decimal | None
    steps_en: list[str]
    steps_hi: list[str]
    ferment_days: int | None
    shelf_life_days: int | None
    apply_every_days: int | None
    apply_method: str | None
    safety_notes_en: str | None
    safety_notes_hi: str | None
    sources: dict[str, Any]
    source_notes: str | None
    todo: list[str]


class PestFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name_en: str | None = Field(default=None, min_length=1, max_length=150)
    name_hi: str | None = Field(default=None, min_length=1, max_length=150)
    crop_slugs: list[str] | None = None
    symptoms_en: str | None = None
    symptoms_hi: str | None = None
    months: list[int] | None = None
    recipe_slugs: list[str] | None = None
    escalate_if: str | None = None
    management_en: str | None = None
    management_hi: str | None = None
    sources: Sources | None = None
    source_notes: str | None = None
    todo: list[str] | None = None

    @field_validator("months")
    @classmethod
    def _months(cls, v: list[int] | None) -> list[int] | None:
        if v is not None and any(m < 1 or m > 12 for m in v):
            raise ValueError("months must be 1-12")
        return v


class PestCreate(PestFields):
    slug: str = Field(pattern=SLUG, max_length=60)
    name_en: str = Field(min_length=1, max_length=150)
    name_hi: str = Field(min_length=1, max_length=150)


class PestOut(ReviewInfo):
    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    crop_slugs: list[str]
    symptoms_en: str | None
    symptoms_hi: str | None
    months: list[int]
    recipe_slugs: list[str]
    escalate_if: str | None
    management_en: str | None
    management_hi: str | None
    sources: dict[str, Any]
    source_notes: str | None
    todo: list[str]


class RuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str | None = None
    params: dict[str, Any] | None = None
    sources: Sources | None = None
    source_notes: str | None = None


class RuleOut(ReviewInfo):
    id: uuid.UUID
    code: str
    description: str
    params: dict[str, Any]
    applies_to: str
    sources: dict[str, Any]
    source_notes: str | None


class CompanionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crop_a: str = Field(pattern=SLUG)
    crop_b: str = Field(pattern=SLUG)
    relation: Literal["good", "avoid"]
    reason_en: str | None = None
    reason_hi: str | None = None
    sources: Sources = {}


class CompanionOut(BaseModel):
    id: uuid.UUID
    crop_a: str
    crop_b: str
    relation: Literal["good", "avoid"]
    reason_en: str | None
    reason_hi: str | None
    status: Status
    sources: dict[str, Any]


class ReviewItem(BaseModel):
    entity: Literal["crop", "recipe", "pest", "rule"]
    id: uuid.UUID
    key: str
    name_en: str
    name_hi: str
    submitted_by: uuid.UUID | None
    submitted_at: datetime | None
    can_approve: bool
    blocked_reason: str | None


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class EngineCrop(BaseModel):
    """What the design engine needs about one crop, for one region (read-only snapshot)."""

    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    status: Status
    family: str | None
    category: str
    layers: list[str]
    seasons: list[str]
    sow_windows: list[dict[str, Any]]
    nursery_days: int | None
    days_to_first_harvest: int | None
    harvest_span_days: int | None
    spacing_row_cm: int | None
    spacing_plant_cm: int | None
    height_max_cm: int | None
    water_need: str | None
    waterlogging_tolerant: bool | None
    expected_yield_kg_per_sqm: float | None
    low_care: bool | None
    tree_spacing_m: float | None = None
    years_to_bear: float | None = None
    price_direct_paise_per_kg: int | None
    price_mandi_paise_per_kg: int | None


class EngineCompanion(BaseModel):
    crop_a: str  # slug
    crop_b: str
    relation: Literal["good", "avoid"]
    reason_en: str | None
    reason_hi: str | None
    status: Status


class CropName(BaseModel):
    id: uuid.UUID
    slug: str
    name_en: str
    name_hi: str
    status: Status
