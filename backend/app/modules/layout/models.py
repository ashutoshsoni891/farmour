"""Tables owned by the layout module (spec section 5: plans, zones, beds)."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedByMixin, IdMixin, TimestampMixin

ZONE_KINDS = "('beds','orchard','rotation','border','water','utility','nursery','path','livestock')"


class Plan(IdMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "plans"
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="draft", server_default="draft")
    start_date: Mapped[date] = mapped_column(Date)
    engine_version: Mapped[str] = mapped_column(String(20))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    __table_args__ = (
        CheckConstraint("status in ('draft','active','archived')", name="status"),
        CheckConstraint("version >= 1", name="version"),
        UniqueConstraint("farm_id", "version", name="farm_version"),
    )


class Zone(IdMixin, Base):
    __tablename__ = "zones"
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(12))
    geom: Mapped[WKBElement] = mapped_column(Geometry("POLYGON", srid=4326))
    area_sqm: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    label: Mapped[str | None] = mapped_column(String(60))
    __table_args__ = (CheckConstraint(f"kind in {ZONE_KINDS}", name="kind"),)


class Bed(IdMixin, Base):
    __tablename__ = "beds"
    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(10))
    geom: Mapped[WKBElement] = mapped_column(Geometry("POLYGON", srid=4326))
    length_m: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    width_m: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    raised: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    orientation_deg: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, server_default="0")
    has_trellis: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
