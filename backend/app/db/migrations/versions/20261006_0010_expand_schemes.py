"""expand: schemes (government schemes and benefits, cited)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schemes",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("state", sa.String(length=60), nullable=True),
        sa.Column("benefit_type", sa.String(length=20), nullable=False),
        sa.Column("name_en", sa.Text(), nullable=False),
        sa.Column("name_hi", sa.Text(), nullable=False),
        sa.Column("gives_en", sa.Text(), nullable=False),
        sa.Column("gives_hi", sa.Text(), nullable=False),
        sa.Column("eligibility_en", sa.Text(), nullable=False),
        sa.Column("eligibility_hi", sa.Text(), nullable=False),
        sa.Column("documents", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("apply_en", sa.Text(), nullable=True),
        sa.Column("apply_hi", sa.Text(), nullable=True),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("rule", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="draft", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("level in ('central','state','district')", name=op.f("ck_schemes_level")),
        sa.CheckConstraint(
            "benefit_type in ('subsidy','loan','interest_rebate','insurance','direct_benefit','training')",
            name=op.f("ck_schemes_benefit_type"),
        ),
        sa.CheckConstraint(
            "status in ('draft','ai_verified','in_review','approved','retired')",
            name=op.f("ck_schemes_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schemes")),
        sa.UniqueConstraint("code", name=op.f("uq_schemes_code")),
    )


def downgrade() -> None:
    op.drop_table("schemes")
