"""expand: bed_layers (crop per layer, bed and season) and the crop-assignment settings

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bed_layers",
        sa.Column("bed_id", sa.UUID(), nullable=False),
        sa.Column("layer", sa.String(length=12), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("season_label", sa.String(length=20), nullable=False),
        sa.Column("crop_id", sa.UUID(), nullable=False),
        sa.Column("planned_sow", sa.Date(), nullable=False),
        sa.Column("plant_count", sa.Integer(), nullable=False),
        sa.Column("spacing_cm", sa.Integer(), nullable=False),
        sa.Column("expected_yield_kg", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("why", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "layer in ('underground','surface','middle','climber','canopy')",
            name=op.f("ck_bed_layers_layer"),
        ),
        sa.CheckConstraint(
            "season in ('kharif','rabi','zaid','perennial')", name=op.f("ck_bed_layers_season")
        ),
        sa.ForeignKeyConstraint(["bed_id"], ["beds.id"], name=op.f("fk_bed_layers_bed_id_beds"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], name=op.f("fk_bed_layers_crop_id_crops")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bed_layers")),
    )
    op.create_index(op.f("ix_bed_layers_bed_id"), "bed_layers", ["bed_id"], unique=False)

    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "layout.plan_days", "value": 365,
         "description": "Length of a plan in days (spec 7: 12 months from the start date)"},
        {"key": "layout.tall_crop_cm", "value": 200,
         "description": "Crops taller than this go only in the north strip, not in beds (spec 7: 2 m)"},
        {"key": "layout.good_companion_bonus", "value": 0.1,
         "description": "Score bonus when a crop grows well with one already in the bed (decision)"},
    ])


def downgrade() -> None:
    op.execute(
        "DELETE FROM settings WHERE key IN "
        "('layout.plan_days','layout.tall_crop_cm','layout.good_companion_bonus')"
    )
    op.drop_index(op.f("ix_bed_layers_bed_id"), table_name="bed_layers")
    op.drop_table("bed_layers")
