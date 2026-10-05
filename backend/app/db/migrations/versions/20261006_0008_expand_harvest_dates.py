"""expand: harvest dates on bed_layers (sow + first harvest + picking period)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bed_layers", sa.Column("harvest_start", sa.Date(), nullable=True))
    op.add_column("bed_layers", sa.Column("harvest_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("bed_layers", "harvest_end")
    op.drop_column("bed_layers", "harvest_start")
