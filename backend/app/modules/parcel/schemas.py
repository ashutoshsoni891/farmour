"""Pydantic v2 contracts for the parcel module."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Soil = Literal["black", "red", "sandy", "clay", "loam", "mixed", "unknown"]
Drainage = Literal["good", "ok", "waterlogs"]


class ParcelOptions(BaseModel):
    """Optional facts about the plot; the site-data card and wizard fill these in."""

    model_config = ConfigDict(extra="forbid")
    north_bearing_deg: float | None = Field(default=None, ge=-360, le=360)
    soil_type: Soil | None = None
    soil_depth_cm: int | None = Field(default=None, ge=0, le=1000)
    drainage: Drainage | None = None
    slope_dir: Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"] | None = None
    terrace_load_kg_per_sqm: float | None = Field(default=None, gt=0, le=2000)
    gate: dict[str, Any] | None = None  # GeoJSON Point
    obstacles: list[dict[str, Any]] | None = None  # GeoJSON features


class ParcelSave(ParcelOptions):
    boundary: dict[str, Any]  # GeoJSON Polygon in WGS84


class Rectangle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["rectangle"] = "rectangle"
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    length_m: float = Field(gt=0, le=1000)
    width_m: float = Field(gt=0, le=1000)
    bearing_deg: float = Field(default=0, ge=-360, le=360)


class FourSides(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["four_sides"] = "four_sides"
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    side_ab_m: float = Field(gt=0, le=1000)
    side_bc_m: float = Field(gt=0, le=1000)
    side_cd_m: float = Field(gt=0, le=1000)
    side_da_m: float = Field(gt=0, le=1000)
    diagonal_ac_m: float = Field(gt=0, le=1500)
    bearing_deg: float = Field(default=0, ge=-360, le=360)


class MeasurementsSave(ParcelOptions):
    shape: Rectangle | FourSides = Field(discriminator="kind")


class ParcelOut(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID
    boundary: dict[str, Any]
    gate: dict[str, Any] | None
    area_sqm: float
    perimeter_m: float | None
    north_bearing_deg: float
    soil_type: Soil | None
    soil_depth_cm: int | None
    drainage: Drainage | None
    slope_dir: str | None
    terrace_load_kg_per_sqm: float | None
    obstacles: list[dict[str, Any]]
    warnings: list[str] = []
    updated_at: datetime
