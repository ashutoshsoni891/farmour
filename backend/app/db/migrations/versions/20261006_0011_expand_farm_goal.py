"""expand: farm goal "low_work", wanted farming methods and a budget band

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_farms_goal"), "farms", type_="check")
    op.create_check_constraint(
        op.f("ck_farms_goal"), "farms", "goal in ('home_food','income','both','low_work')"
    )
    op.add_column(
        "farms",
        sa.Column("methods", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
    )
    op.add_column("farms", sa.Column("budget_band", sa.String(length=6), nullable=True))
    op.create_check_constraint(
        op.f("ck_farms_budget_band"), "farms", "budget_band in ('low','medium','high')"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_farms_budget_band"), "farms", type_="check")
    op.drop_column("farms", "budget_band")
    op.drop_column("farms", "methods")
    op.execute("UPDATE farms SET goal = 'both' WHERE goal = 'low_work'")
    op.drop_constraint(op.f("ck_farms_goal"), "farms", type_="check")
    op.create_check_constraint(
        op.f("ck_farms_goal"), "farms", "goal in ('home_food','income','both')"
    )
