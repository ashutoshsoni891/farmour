"""Tables owned by the site module (spec section 17)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class SiteFact(IdMixin, TimestampMixin, Base):
    __tablename__ = "site_facts"
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(60))
    value: Mapped[Any] = mapped_column(JSONB)
    unit: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(30))
    method: Mapped[str | None] = mapped_column(String(60))
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    attribution: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(10), default="derived", server_default="derived")
    __table_args__ = (
        UniqueConstraint("farm_id", "key", "source", name="farm_key_source"),
        CheckConstraint("status in ('derived','confirmed','edited','rejected')", name="status"),
    )


class SiteBuild(Base):
    __tablename__ = "site_builds"
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(10))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    __table_args__ = (CheckConstraint("status in ('running','done','failed')", name="status"),)


class GeoCache(Base):
    """Results shared by nearby farms: one entry per 0.01 degree cell and source."""

    __tablename__ = "geo_cache"
    cell_key: Mapped[str] = mapped_column(String(30), primary_key=True)
    source: Mapped[str] = mapped_column(String(30), primary_key=True)
    payload: Mapped[Any] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Mandi(IdMixin, TimestampMixin, Base):
    __tablename__ = "mandis"
    name: Mapped[str] = mapped_column(String(150))
    district: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(60))
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    geocode_tried: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    __table_args__ = (UniqueConstraint("name", "district", "state", name="market"),)


class MandiPrice(IdMixin, Base):
    """Daily prices ingested from Agmarknet. Plans read this table, never the live API."""

    __tablename__ = "mandi_prices"
    mandi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandis.id", ondelete="CASCADE"))
    commodity: Mapped[str] = mapped_column(String(100))
    variety: Mapped[str] = mapped_column(String(100), default="", server_default="")
    crop_id: Mapped[uuid.UUID | None]  # set once a library crop maps to this commodity
    price_date: Mapped[date] = mapped_column(Date)
    min_paise: Mapped[int | None] = mapped_column(BigInteger)
    max_paise: Mapped[int | None] = mapped_column(BigInteger)
    modal_paise: Mapped[int | None] = mapped_column(BigInteger)
    unit: Mapped[str] = mapped_column(String(10), default="quintal", server_default="quintal")
    __table_args__ = (
        UniqueConstraint("mandi_id", "commodity", "variety", "price_date", name="price_day"),
    )


class DistrictRegion(IdMixin, Base):
    """Curated district -> region lookup (spec section 17: region / agro-climatic zone)."""

    __tablename__ = "district_regions"
    state: Mapped[str] = mapped_column(String(60))
    district: Mapped[str] = mapped_column(String(100))
    region_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("regions.id"))
    __table_args__ = (UniqueConstraint("state", "district", name="district"),)


class GroundwaterBlock(IdMixin, Base):
    """CGWB assessment category per block (or per district when `block` is empty)."""

    __tablename__ = "groundwater_blocks"
    state: Mapped[str] = mapped_column(String(60))
    district: Mapped[str] = mapped_column(String(100))
    block: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20))
    assessed_year: Mapped[str | None] = mapped_column(String(9))
    source_url: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        CheckConstraint(
            "category in ('safe','semi_critical','critical','over_exploited','saline')",
            name="category",
        ),
    )


class Scheme(IdMixin, TimestampMixin, Base):
    """Government schemes and benefits (spec 17 `schemes`, extended by docs/vision.md pillar 6).

    Every statement has a cited source; `status` follows the crop library (draft -> ai_verified ->
    approved). Eligibility is structured (`rule`) so the plan can be matched without an LLM."""

    __tablename__ = "schemes"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    level: Mapped[str] = mapped_column(String(10))
    state: Mapped[str | None] = mapped_column(String(60))
    benefit_type: Mapped[str] = mapped_column(String(20))
    name_en: Mapped[str] = mapped_column(Text)
    name_hi: Mapped[str] = mapped_column(Text)
    gives_en: Mapped[str] = mapped_column(Text)
    gives_hi: Mapped[str] = mapped_column(Text)
    eligibility_en: Mapped[str] = mapped_column(Text)
    eligibility_hi: Mapped[str] = mapped_column(Text)
    documents: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    apply_en: Mapped[str | None] = mapped_column(Text)
    apply_hi: Mapped[str | None] = mapped_column(Text)
    apply_url: Mapped[str | None] = mapped_column(Text)
    rule: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    checked_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), default="draft", server_default="draft")
    __table_args__ = (
        CheckConstraint("level in ('central','state','district')", name="level"),
        CheckConstraint(
            "benefit_type in ('subsidy','loan','interest_rebate','insurance',"
            "'direct_benefit','training')",
            name="benefit_type",
        ),
        CheckConstraint(
            "status in ('draft','ai_verified','in_review','approved','retired')", name="status"
        ),
    )
