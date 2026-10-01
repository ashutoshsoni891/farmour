"""Tables owned by the parcel module (spec section 5)."""

import uuid
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedByMixin, IdMixin, TimestampMixin


class Parcel(IdMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "parcels"
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), unique=True
    )
    boundary: Mapped[WKBElement] = mapped_column(Geometry("POLYGON", srid=4326))
    gate: Mapped[WKBElement | None] = mapped_column(Geometry("POINT", srid=4326))
    area_sqm: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    perimeter_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    north_bearing_deg: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0, server_default="0")
    soil_type: Mapped[str | None] = mapped_column(String(10))
    soil_depth_cm: Mapped[int | None] = mapped_column(Integer)
    drainage: Mapped[str | None] = mapped_column(String(10))
    slope_dir: Mapped[str | None] = mapped_column(String(2))
    terrace_load_kg_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    obstacles: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    __table_args__ = (
        CheckConstraint(
            "soil_type in ('black','red','sandy','clay','loam','mixed','unknown')", name="soil_type"
        ),
        CheckConstraint("drainage in ('good','ok','waterlogs')", name="drainage"),
        CheckConstraint("area_sqm > 0", name="area"),
    )
