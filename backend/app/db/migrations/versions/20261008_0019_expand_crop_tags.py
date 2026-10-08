"""expand: crops.tags (what a crop is used for: medicinal, ayurvedic, aromatic)

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-08
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crops",
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
    )
    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "layout.medicinal_bed_share", "value": 0.25,
         "description": "Share of beds given to medicinal herbs when the owner chose the medicinal"
                        " method (decision 2026-10-08)"},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'layout.medicinal_bed_share'")
    op.drop_column("crops", "tags")
