import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, SoftDeleteMixin, TimestampMixin


class User(IdMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    language: Mapped[str] = mapped_column(String(2), default="hi", server_default="hi")
    unit_pref: Mapped[str] = mapped_column(String(5), default="sqft", server_default="sqft")
    bigha_sqft: Mapped[Decimal | None] = mapped_column(Numeric)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_agronomist: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    keycloak_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    session_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    __table_args__ = (
        CheckConstraint("language in ('en','hi')", name="language"),
        CheckConstraint("unit_pref in ('sqft','acre','bigha','sqm')", name="unit_pref"),
        CheckConstraint("bigha_sqft is null or bigha_sqft > 0", name="bigha_sqft"),
    )


class ChannelAccount(IdMixin, TimestampMixin, Base):
    """A user's account on a messaging channel (e.g. a Telegram chat id)."""

    __tablename__ = "channel_accounts"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(100))
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    __table_args__ = (UniqueConstraint("channel", "external_id", name="channel_external"),)


class LoginLink(IdMixin, Base):
    """Single-use caretaker login link. Only a SHA-256 hash of the token is stored."""

    __tablename__ = "login_links"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
