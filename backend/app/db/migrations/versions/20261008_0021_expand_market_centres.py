"""expand: market centres (herb mandis and portals where a crop can be sold or priced)

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-08
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_centres",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_hi", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column("district", sa.String(length=80), nullable=True),
        sa.Column("crops", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("note_en", sa.Text(), nullable=True),
        sa.Column("note_hi", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="draft", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "kind in ('herb_mandi','portal','support')", name=op.f("ck_market_centres_kind")
        ),
        sa.CheckConstraint(
            "status in ('draft','ai_verified','in_review','approved','retired')",
            name=op.f("ck_market_centres_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_centres")),
        sa.UniqueConstraint("code", name=op.f("uq_market_centres_code")),
    )


def downgrade() -> None:
    op.drop_table("market_centres")
