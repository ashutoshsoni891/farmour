"""expand: plan options (option code and generation batch on plans) and bed size choices

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("option", sa.String(length=20), nullable=True))
    op.add_column("plans", sa.Column("batch", sa.Integer(), nullable=True))
    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "layout.bed_widths", "value": {"narrow": 0.9, "standard": 1.2, "wide": 1.5},
         "description": "Bed width choices in metres (decision: standard is the spec's 1.2 m, "
                        "narrow is the minimum bed width, wide is a product default; agronomist to confirm)"},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'layout.bed_widths'")
    op.drop_column("plans", "batch")
    op.drop_column("plans", "option")
