"""Platform tables shared by all modules: settings, audit log, outbox, jobs, regions."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID | None]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_log"
    actor_id: Mapped[uuid.UUID | None]
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    before: Mapped[dict[str, Any] | None]
    after: Mapped[dict[str, Any] | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_audit_log_entity", "entity", "entity_id"),)


class OutboxEvent(IdMixin, Base):
    __tablename__ = "outbox"
    event: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict[str, Any]]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_to: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    __table_args__ = (
        Index(
            "ix_outbox_pending",
            "next_attempt_at",
            postgresql_where="delivered_at IS NULL",
        ),
    )


class JobRun(IdMixin, Base):
    __tablename__ = "jobs"
    name: Mapped[str] = mapped_column(String(100))
    run_key: Mapped[str] = mapped_column(String(200), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    last_error: Mapped[str | None] = mapped_column(Text)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Region(IdMixin, TimestampMixin, Base):
    __tablename__ = "regions"
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_hi: Mapped[str] = mapped_column(String(100))
