"""expand: non-chemical management steps on pests and diseases

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-07
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pests", sa.Column("management_en", sa.Text(), nullable=True))
    op.add_column("pests", sa.Column("management_hi", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pests", "management_hi")
    op.drop_column("pests", "management_en")
