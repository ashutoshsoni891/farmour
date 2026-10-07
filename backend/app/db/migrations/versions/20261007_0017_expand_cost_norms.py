"""expand: cost norms (setup cost and subsidy rate per component, cited)

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-07
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cost_norms",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("group", sa.String(length=20), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_hi", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(length=10), nullable=False),
        sa.Column("tiers", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("subsidy_pct", sa.Integer(), nullable=True),
        sa.Column("subsidy_max_qty", sa.Numeric(12, 2), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("note_en", sa.Text(), nullable=True),
        sa.Column("note_hi", sa.Text(), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="draft", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("unit in ('sqm','ha','unit')", name=op.f("ck_cost_norms_unit")),
        sa.CheckConstraint(
            "status in ('draft','ai_verified','in_review','approved','retired')",
            name=op.f("ck_cost_norms_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_norms")),
        sa.UniqueConstraint("code", name=op.f("uq_cost_norms_code")),
    )


def downgrade() -> None:
    op.drop_table("cost_norms")
