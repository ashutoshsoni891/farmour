"""expand: parcels (M2a)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parcels",
        sa.Column("farm_id", sa.UUID(), nullable=False),
        sa.Column("boundary", Geometry("POLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("gate", Geometry("POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column("area_sqm", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("perimeter_m", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "north_bearing_deg", sa.Numeric(precision=6, scale=2), server_default="0", nullable=False
        ),
        sa.Column("soil_type", sa.String(length=10), nullable=True),
        sa.Column("soil_depth_cm", sa.Integer(), nullable=True),
        sa.Column("drainage", sa.String(length=10), nullable=True),
        sa.Column("slope_dir", sa.String(length=2), nullable=True),
        sa.Column("terrace_load_kg_per_sqm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("obstacles", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("area_sqm > 0", name=op.f("ck_parcels_area")),
        sa.CheckConstraint("drainage in ('good','ok','waterlogs')", name=op.f("ck_parcels_drainage")),
        sa.CheckConstraint(
            "soil_type in ('black','red','sandy','clay','loam','mixed','unknown')",
            name=op.f("ck_parcels_soil_type"),
        ),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], name=op.f("fk_parcels_farm_id_farms"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parcels")),
        sa.UniqueConstraint("farm_id", name=op.f("uq_parcels_farm_id")),
    )
    op.execute("CREATE INDEX idx_parcels_boundary ON parcels USING gist (boundary)")
    op.execute("CREATE INDEX idx_parcels_gate ON parcels USING gist (gate)")

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
                "key": "parcel.limits",
                "value": {"min_area_sqm": 5, "max_area_sqm": 20250, "min_side_m": 1},
                "description": "Parcel validation limits (spec 7, step 1; MVP cap 5 acres)",
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'parcel.limits'")
    op.drop_table("parcels")
