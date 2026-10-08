"""expand: field plantings (crops on the plots of the rotation field) and their settings

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-08
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "field_plantings",
        sa.Column("zone_id", sa.UUID(), nullable=False),
        sa.Column("plot_code", sa.String(length=10), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("area_sqm", sa.Numeric(12, 2), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("season_label", sa.String(length=20), nullable=False),
        sa.Column("crop_id", sa.UUID(), nullable=False),
        sa.Column("planned_sow", sa.Date(), nullable=False),
        sa.Column("harvest_start", sa.Date(), nullable=True),
        sa.Column("harvest_end", sa.Date(), nullable=True),
        sa.Column("plant_count", sa.Integer(), nullable=True),
        sa.Column("expected_yield_kg", sa.Numeric(12, 2), nullable=False),
        sa.Column("why", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "season in ('kharif','rabi','zaid','perennial')",
            name=op.f("ck_field_plantings_season"),
        ),
        sa.ForeignKeyConstraint(
            ["zone_id"], ["zones.id"], name=op.f("fk_field_plantings_zone_id_zones"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], name=op.f("fk_field_plantings_crop_id_crops")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_plantings")),
    )
    op.create_index(op.f("ix_field_plantings_zone_id"), "field_plantings", ["zone_id"], unique=False)
    op.execute("CREATE INDEX idx_field_plantings_geom ON field_plantings USING gist (geom)")
    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "layout.field_plots", "value": 2,
         "description": "Plots the rotation field is cut into, so each season can grow two crops"
                        " (decision 2026-10-08)"},
        {"key": "layout.field_min_plot_sqm", "value": 100,
         "description": "A rotation field smaller than this many sqm per plot is not cut up"
                        " (decision 2026-10-08)"},
    ])


def downgrade() -> None:
    op.execute(
        "DELETE FROM settings WHERE key IN ('layout.field_plots','layout.field_min_plot_sqm')"
    )
    op.execute("DROP INDEX IF EXISTS idx_field_plantings_geom")
    op.drop_index(op.f("ix_field_plantings_zone_id"), table_name="field_plantings")
    op.drop_table("field_plantings")
