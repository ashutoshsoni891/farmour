"""expand: zone_plants (trees in the orchard strip, hedge plants on the border)

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "zone_plants",
        sa.Column("zone_id", sa.UUID(), nullable=False),
        sa.Column("crop_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("spacing_m", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("plant_on", sa.Date(), nullable=False),
        sa.Column("first_harvest", sa.Date(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint("kind in ('tree','hedge')", name=op.f("ck_zone_plants_kind")),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name=op.f("fk_zone_plants_zone_id_zones"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crop_id"], ["crops.id"], name=op.f("fk_zone_plants_crop_id_crops")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zone_plants")),
    )
    op.create_index(op.f("ix_zone_plants_zone_id"), "zone_plants", ["zone_id"], unique=False)
    op.execute("CREATE INDEX idx_zone_plants_geom ON zone_plants USING gist (geom)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_zone_plants_geom")
    op.drop_index(op.f("ix_zone_plants_zone_id"), table_name="zone_plants")
    op.drop_table("zone_plants")
