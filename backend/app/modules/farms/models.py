import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedByMixin, IdMixin, SoftDeleteMixin, TimestampMixin


class Organization(IdMixin, TimestampMixin, Base):
    """FPO / NGO grouping of farms. Unused in the MVP (spec section 16)."""

    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))


class Farm(IdMixin, TimestampMixin, CreatedByMixin, SoftDeleteMixin, Base):
    __tablename__ = "farms"
    name: Mapped[str] = mapped_column(String(200))
    site_type: Mapped[str | None] = mapped_column(String(10))
    district: Mapped[str | None] = mapped_column(String(100))
    village: Mapped[str | None] = mapped_column(String(100))
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    goal: Mapped[str | None] = mapped_column(String(10))
    budget_setup_paise: Mapped[int | None] = mapped_column(BigInteger)
    budget_monthly_paise: Mapped[int | None] = mapped_column(BigInteger)
    labour: Mapped[str | None] = mapped_column(String(10))
    water_source: Mapped[str | None] = mapped_column(String(10))
    water_summer_lpd: Mapped[int | None] = mapped_column(Integer)
    electricity: Mapped[bool | None] = mapped_column(Boolean)
    livestock: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # farming methods the owner wants (multilayer, orchard, flowers, natural, polyhouse, integrated)
    methods: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    budget_band: Mapped[str | None] = mapped_column(String(6))
    region_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("regions.id"))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}"
    )
    __table_args__ = (
        CheckConstraint("site_type in ('ground','terrace')", name="site_type"),
        CheckConstraint("goal in ('home_food','income','both','low_work')", name="goal"),
        CheckConstraint("budget_band in ('low','medium','high')", name="budget_band"),
        CheckConstraint("labour in ('self','family','caretaker','mixed')", name="labour"),
        CheckConstraint(
            "water_source in ('bore','well','canal','municipal','rain_only')", name="water_source"
        ),
        CheckConstraint("budget_setup_paise >= 0", name="budget_setup"),
        CheckConstraint("budget_monthly_paise >= 0", name="budget_monthly"),
    )


class FarmMember(TimestampMixin, Base):
    __tablename__ = "farm_members"
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(10))
    caretaker_sees_money: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    __table_args__ = (CheckConstraint("role in ('owner','caretaker')", name="role"),)


class Invite(IdMixin, CreatedByMixin, Base):
    __tablename__ = "invites"
    farm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farms.id", ondelete="CASCADE"), index=True
    )
    phone: Mapped[str] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(10))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("role in ('caretaker')", name="role"),)
