"""expand: polyhouse zone kind, covered beds, and the size of optional zones

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "kind in ('beds','orchard','rotation','border','water','utility','nursery','path','livestock')"
NEW = (
    "kind in ('beds','orchard','rotation','border','water','utility','nursery','path','livestock',"
    "'polyhouse')"
)


def upgrade() -> None:
    op.drop_constraint(op.f("ck_zones_kind"), "zones", type_="check")
    op.create_check_constraint(op.f("ck_zones_kind"), "zones", NEW)
    op.add_column(
        "beds", sa.Column("protected", sa.Boolean(), server_default="false", nullable=False)
    )
    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "layout.extra_zones", "value": {"polyhouse": 8, "livestock": 5},
         "description": "Percent of the plot for zones the owner asks for in the goal step "
                        "(product defaults, decision 2026-10-06; agronomist to confirm)"},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'layout.extra_zones'")
    op.drop_column("beds", "protected")
    op.execute("DELETE FROM zones WHERE kind = 'polyhouse'")
    op.drop_constraint(op.f("ck_zones_kind"), "zones", type_="check")
    op.create_check_constraint(op.f("ck_zones_kind"), "zones", OLD)
