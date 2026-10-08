"""Pydantic contracts for the layout module."""

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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
    protected: bool = False  # a covered bed inside the polyhouse


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
    harvest_start: date | None
    harvest_end: date | None
    plant_count: int
    spacing_cm: int
    expected_yield_kg: float
    why: dict[str, Any]


class FieldPlantingOut(BaseModel):
    """One crop on one plot of the rotation field for one season."""

    plot_code: str
    geometry: dict[str, Any]
    area_sqm: float
    season: str
    season_label: str
    crop: CropRef
    planned_sow: date
    harvest_start: date | None
    harvest_end: date | None
    plant_count: int | None
    expected_yield_kg: float
    why: dict[str, Any]


class PerennialOut(BaseModel):
    """All trees (or hedge plants) of one crop: where they stand, when they go in and first bear."""

    crop: CropRef
    kind: str  # tree | hedge
    count: int
    spacing_m: float
    plant_on: date
    first_harvest: date | None
    yearly_kg_when_bearing: float | None
    points: dict[str, Any]  # GeoJSON MultiPoint


class PlanWarning(BaseModel):
    code: str
    message_key: str
    params: dict[str, Any] = {}


class PlanOut(BaseModel):
    id: uuid.UUID
    option: str | None
    custom: bool = False  # the owner resized land uses, changed bed size or swapped a crop
    bed_size: str = "standard"
    share_delta: dict[str, int] = {}  # owner's change to the option's land use, in points
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
    fields: list[FieldPlantingOut] = []  # crops on the rotation-field plots
    perennials: list[PerennialOut] = []
    uses_ai_checked: bool
    trellis_height_m: float | None = None
    bed_width_m: float | None = None
    path_width_m: float | None = None
    machan_guide: list[dict[str, Any]] = []
    created_at: datetime


Level = Literal["low", "medium", "high"]


class OptionMetrics(BaseModel):
    beds: int
    bed_area_sqm: float
    crops_total: int
    crops_min_season: int
    harvest_kg: float
    water_index: float  # relative: bed area x water need x days in the ground
    work_index: float  # relative: bed area x days under crops (sowing, care, picking)
    plantings: int = 0
    trees: int = 0
    tree_species: int = 0
    hedge_plants: int = 0
    field_plantings: int = 0
    field_kg: float = 0.0
    trees_yearly_kg: float = 0.0  # once the trees bear


class OptionOut(BaseModel):
    plan_id: uuid.UUID
    option: str
    status: PlanStatus
    custom: bool
    recommended: bool
    suits: list[str]  # why it suits this farm: "goal", "labour", "water"
    metrics: OptionMetrics
    levels: dict[str, Level]  # harvest, water, work compared across the options
    land_use: dict[str, float]  # zone kind -> share of the plot (0-1)


class OptionsOut(BaseModel):
    batch: int | None
    active_plan_id: uuid.UUID | None
    options: list[OptionOut]


ZoneShare = Literal["orchard", "water", "utility_nursery", "rotation"]
BedSize = Literal["narrow", "standard", "wide"]


class AdjustIn(BaseModel):
    """Owner's changes to an option: land use in percentage points, and bed size."""

    model_config = ConfigDict(extra="forbid")
    share_delta: dict[ZoneShare, int] = {}
    bed_size: BedSize = "standard"


class SwapIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    season_label: str = Field(min_length=1, max_length=20)
    layer: Literal["underground", "surface", "middle", "climber"]
    crop_slug: str = Field(min_length=1, max_length=60)


class AlternativeOut(BaseModel):
    crop: CropRef
    current: bool
    planned_sow: date
    harvest_start: date
    harvest_end: date
    plant_count: int
    expected_yield_kg: float
