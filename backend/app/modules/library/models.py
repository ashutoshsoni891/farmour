"""Tables owned by the library module (spec section 6).

Reviewed entities share `ReviewMixin`: a status workflow, a revision counter bumped on each
approval, and per-field `sources` so every agronomy value can be traced to where it came from.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedByMixin, IdMixin, TimestampMixin

STATUSES = "('draft','ai_verified','in_review','approved','retired')"


class ReviewMixin(CreatedByMixin):
    status: Mapped[str] = mapped_column(String(12), default="draft", server_default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    source_notes: Mapped[str | None] = mapped_column(Text)
    todo: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    submitted_by: Mapped[uuid.UUID | None]
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Crop(IdMixin, TimestampMixin, ReviewMixin, Base):
    __tablename__ = "crops"
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_hi: Mapped[str] = mapped_column(String(100))
    scientific_name: Mapped[str | None] = mapped_column(String(150))
    family: Mapped[str | None] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(20))
    layers: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    seasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    nursery_days: Mapped[int | None]
    days_to_first_harvest: Mapped[int | None]
    harvest_span_days: Mapped[int | None]
    spacing_row_cm: Mapped[int | None]
    spacing_plant_cm: Mapped[int | None]
    rows_per_1_2m_bed: Mapped[int | None]
    height_max_cm: Mapped[int | None]
    root_depth_cm: Mapped[int | None]
    sun: Mapped[str | None] = mapped_column(String(15))
    water_need: Mapped[str | None] = mapped_column(String(10))
    water_l_per_sqm_day: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    heat_tolerance_c: Mapped[int | None]
    cold_tolerance_c: Mapped[int | None]
    waterlogging_tolerant: Mapped[bool | None] = mapped_column(Boolean)
    terrace_ok: Mapped[bool | None] = mapped_column(Boolean)
    min_container_depth_cm: Mapped[int | None]
    expected_yield_kg_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    yield_unit: Mapped[str] = mapped_column(String(10), default="kg", server_default="kg")
    unit_to_kg: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # e.g. {"bunch": 0.25}
    years_to_bear: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    lifespan_years: Mapped[int | None]
    tree_spacing_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    canopy_diameter_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    low_care: Mapped[bool | None] = mapped_column(Boolean)
    __table_args__ = (
        CheckConstraint(
            "category in ('vegetable','leafy','root','spice','fruit_tree','fruit_short','pulse',"
            "'cereal','millet','oilseed','herb','border','green_manure','flower')",
            name="category",
        ),
        CheckConstraint(
            "layers <@ ARRAY['underground','surface','middle','climber','canopy']::varchar[]",
            name="layers",
        ),
        CheckConstraint(
            "seasons <@ ARRAY['kharif','rabi','zaid','perennial']::varchar[]", name="seasons"
        ),
        CheckConstraint("sun in ('full','partial','shade_tolerant')", name="sun"),
        CheckConstraint("water_need in ('low','medium','high')", name="water_need"),
        CheckConstraint(f"status in {STATUSES}", name="status"),
    )


class CropRegional(IdMixin, TimestampMixin, Base):
    """Region-specific crop data (spec section 16: region_id on sow windows and prices)."""

    __tablename__ = "crop_regional"
    crop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"))
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))
    sow_windows: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    price_mandi_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    price_direct_paise_per_kg: Mapped[int | None] = mapped_column(BigInteger)
    price_updated_on: Mapped[date | None] = mapped_column(Date)
    agmarknet_commodity: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    __table_args__ = (UniqueConstraint("crop_id", "region_id", name="crop_region"),)


class CropVariety(IdMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "crop_varieties"
    crop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    days_to_first_harvest: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="draft", server_default="draft")
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    __table_args__ = (CheckConstraint(f"status in {STATUSES}", name="status"),)


class Companion(IdMixin, TimestampMixin, CreatedByMixin, Base):
    """Stored with crop_a < crop_b (by id) so each pair appears once."""

    __tablename__ = "companions"
    crop_a: Mapped[uuid.UUID] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"))
    crop_b: Mapped[uuid.UUID] = mapped_column(ForeignKey("crops.id", ondelete="CASCADE"))
    relation: Mapped[str] = mapped_column(String(5))
    reason_en: Mapped[str | None] = mapped_column(Text)
    reason_hi: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="draft", server_default="draft")
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    __table_args__ = (
        UniqueConstraint("crop_a", "crop_b", name="pair"),
        CheckConstraint("crop_a < crop_b", name="ordered"),
        CheckConstraint("relation in ('good','avoid')", name="relation"),
        CheckConstraint(f"status in {STATUSES}", name="status"),
    )


class Recipe(IdMixin, TimestampMixin, ReviewMixin, Base):
    __tablename__ = "recipes"
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_hi: Mapped[str] = mapped_column(String(100))
    ingredients: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    per_area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    steps_en: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    steps_hi: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    ferment_days: Mapped[int | None]
    shelf_life_days: Mapped[int | None]
    apply_every_days: Mapped[int | None]
    apply_method: Mapped[str | None] = mapped_column(String(30))
    safety_notes_en: Mapped[str | None] = mapped_column(Text)
    safety_notes_hi: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint(f"status in {STATUSES}", name="status"),)


class Pest(IdMixin, TimestampMixin, ReviewMixin, Base):
    __tablename__ = "pests"
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name_en: Mapped[str] = mapped_column(String(150))
    name_hi: Mapped[str] = mapped_column(String(150))
    crop_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Base.type_annotation_map[uuid.UUID]), default=list, server_default="{}"
    )
    symptoms_en: Mapped[str | None] = mapped_column(Text)
    symptoms_hi: Mapped[str | None] = mapped_column(Text)
    months: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, server_default="{}")
    recipe_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(Base.type_annotation_map[uuid.UUID]), default=list, server_default="{}"
    )
    escalate_if: Mapped[str | None] = mapped_column(Text)
    management_en: Mapped[str | None] = mapped_column(Text)
    management_hi: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (CheckConstraint(f"status in {STATUSES}", name="status"),)


class Rule(IdMixin, TimestampMixin, ReviewMixin, Base):
    """Design-engine rules and defaults (spec section 7), editable without a deploy."""

    __tablename__ = "rules"
    code: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    applies_to: Mapped[str] = mapped_column(String(30))
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    __table_args__ = (CheckConstraint(f"status in {STATUSES}", name="status"),)


class LibraryRevision(IdMixin, Base):
    """Snapshot of an entry at each approval, so plans can pin exact library versions."""

    __tablename__ = "library_revisions"
    entity: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[uuid.UUID]
    revision: Mapped[int]
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("entity", "entity_id", "revision", name="entity_rev"),)


class LibraryChunk(IdMixin, TimestampMixin, Base):
    """Retrieval chunks of approved entries (filled by the AI module, M7)."""

    __tablename__ = "library_chunks"
    source_table: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[uuid.UUID] = mapped_column(index=True)
    lang: Mapped[str] = mapped_column(String(2))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    status: Mapped[str] = mapped_column(String(10), default="approved", server_default="approved")
