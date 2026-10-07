"""expand: Krishi Vigyan Kendra directory (cited contact details)

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-07
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kvks",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("district", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("address_en", sa.Text(), nullable=False),
        sa.Column("phones", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="draft", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('draft','ai_verified','in_review','approved','retired')",
            name=op.f("ck_kvks_status"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kvks")),
        sa.UniqueConstraint("code", name=op.f("uq_kvks_code")),
    )


def downgrade() -> None:
    op.drop_table("kvks")
