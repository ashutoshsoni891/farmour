"""expand: plans, zones and beds (M3 layout) and the layout settings

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ZONE_KINDS = "('beds','orchard','rotation','border','water','utility','nursery','path','livestock')"


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("farm_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("engine_version", sa.String(length=20), nullable=False),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('draft','active','archived')", name=op.f("ck_plans_status")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_plans_version")),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], name=op.f("fk_plans_farm_id_farms"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
        sa.UniqueConstraint("farm_id", "version", name=op.f("uq_plans_farm_version")),
    )
    op.create_index(op.f("ix_plans_farm_id"), "plans", ["farm_id"], unique=False)
    op.create_table(
        "zones",
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("area_sqm", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(f"kind in {ZONE_KINDS}", name=op.f("ck_zones_kind")),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name=op.f("fk_zones_plan_id_plans"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zones")),
    )
    op.create_index(op.f("ix_zones_plan_id"), "zones", ["plan_id"], unique=False)
    op.execute("CREATE INDEX idx_zones_geom ON zones USING gist (geom)")
    op.create_table(
        "beds",
        sa.Column("zone_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("length_m", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("width_m", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("raised", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("orientation_deg", sa.Numeric(precision=6, scale=2), server_default="0", nullable=False),
        sa.Column("has_trellis", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], name=op.f("fk_beds_zone_id_zones"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_beds")),
    )
    op.create_index(op.f("ix_beds_zone_id"), "beds", ["zone_id"], unique=False)
    op.execute("CREATE INDEX idx_beds_geom ON beds USING gist (geom)")

    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "layout.gate_opening_m", "value": 3,
         "description": "Width of the gate gap left in the border (decision; spec 7 only says skip the gate segment)"},
        {"key": "layout.nursery_share_of_utility", "value": 0.5,
         "description": "Share of the utility + nursery area given to the nursery (decision; spec gives one combined share)"},
        {"key": "layout.zone_aspect", "value": 1.5,
         "description": "Length : width of carved pond, utility, nursery and rotation pieces (decision)"},
        {"key": "layout.area_tolerance_pct", "value": 2,
         "description": "Zone area tolerance when sizing a zone to its share (spec 7: +/-2%)"},
        {"key": "layout.min_beds_share_pct", "value": 50,
         "description": "A plan needs at least this % of the beds-zone target left, else optional zones are dropped (decision)"},
        {"key": "layout.min_beds_axis_extent_m", "value": 3,
         "description": "Beds zone narrower than this north-south run along the zone's main axis (spec 7)"},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key LIKE 'layout.%'")
    op.execute("DROP INDEX IF EXISTS idx_beds_geom")
    op.drop_index(op.f("ix_beds_zone_id"), table_name="beds")
    op.drop_table("beds")
    op.execute("DROP INDEX IF EXISTS idx_zones_geom")
    op.drop_index(op.f("ix_zones_plan_id"), table_name="zones")
    op.drop_table("zones")
    op.drop_index(op.f("ix_plans_farm_id"), table_name="plans")
    op.drop_table("plans")
