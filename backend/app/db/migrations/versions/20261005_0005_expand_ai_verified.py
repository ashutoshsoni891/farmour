"""expand: library status `ai_verified` and the beta flag that lets plans use it

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ["crops", "pests", "recipes", "companions", "crop_varieties", "rules"]
NEW = "status in ('draft','ai_verified','in_review','approved','retired')"
OLD = "status in ('draft','in_review','approved','retired')"


def upgrade() -> None:
    for table in TABLES:
        op.alter_column(table, "status", type_=sa.String(length=12))
        op.drop_constraint(op.f(f"ck_{table}_status"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_status"), table, NEW)
    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        settings,
        [
            {
                "key": "library.allow_ai_verified",
                "value": False,
                "description": "Beta: plans may use AI-checked library entries (shown as not yet "
                "reviewed by an expert)",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'library.allow_ai_verified'")
    for table in TABLES:
        op.execute(f"UPDATE {table} SET status = 'draft' WHERE status = 'ai_verified'")  # noqa: S608 (fixed table list)
        op.drop_constraint(op.f(f"ck_{table}_status"), table, type_="check")
        op.create_check_constraint(op.f(f"ck_{table}_status"), table, OLD)
        op.alter_column(table, "status", type_=sa.String(length=10))
