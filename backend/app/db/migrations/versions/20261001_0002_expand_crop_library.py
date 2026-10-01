"""expand: crop library (M1)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01
Phase: expand
"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crops",
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("name_hi", sa.String(length=100), nullable=False),
        sa.Column("scientific_name", sa.String(length=150), nullable=True),
        sa.Column("family", sa.String(length=40), nullable=True),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("layers", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("seasons", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("nursery_days", sa.Integer(), nullable=True),
        sa.Column("days_to_first_harvest", sa.Integer(), nullable=True),
        sa.Column("harvest_span_days", sa.Integer(), nullable=True),
        sa.Column("spacing_row_cm", sa.Integer(), nullable=True),
        sa.Column("spacing_plant_cm", sa.Integer(), nullable=True),
        sa.Column("rows_per_1_2m_bed", sa.Integer(), nullable=True),
        sa.Column("height_max_cm", sa.Integer(), nullable=True),
        sa.Column("root_depth_cm", sa.Integer(), nullable=True),
        sa.Column("sun", sa.String(length=15), nullable=True),
        sa.Column("water_need", sa.String(length=10), nullable=True),
        sa.Column("water_l_per_sqm_day", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("heat_tolerance_c", sa.Integer(), nullable=True),
        sa.Column("cold_tolerance_c", sa.Integer(), nullable=True),
        sa.Column("waterlogging_tolerant", sa.Boolean(), nullable=True),
        sa.Column("terrace_ok", sa.Boolean(), nullable=True),
        sa.Column("min_container_depth_cm", sa.Integer(), nullable=True),
        sa.Column("expected_yield_kg_per_sqm", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("yield_unit", sa.String(length=10), server_default="kg", nullable=False),
        sa.Column("unit_to_kg", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("years_to_bear", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("lifespan_years", sa.Integer(), nullable=True),
        sa.Column("tree_spacing_m", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("canopy_diameter_m", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("low_care", sa.Boolean(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("todo", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "category in ('vegetable','leafy','root','spice','fruit_tree','fruit_short','pulse','cereal','millet','oilseed','herb','border','green_manure','flower')",
            name=op.f("ck_crops_category"),
        ),
        sa.CheckConstraint(
            "layers <@ ARRAY['underground','surface','middle','climber','canopy']::varchar[]",
            name=op.f("ck_crops_layers"),
        ),
        sa.CheckConstraint(
            "seasons <@ ARRAY['kharif','rabi','zaid','perennial']::varchar[]",
            name=op.f("ck_crops_seasons"),
        ),
        sa.CheckConstraint(
            "status in ('draft','in_review','approved','retired')", name=op.f("ck_crops_status")
        ),
        sa.CheckConstraint("sun in ('full','partial','shade_tolerant')", name=op.f("ck_crops_sun")),
        sa.CheckConstraint(
            "water_need in ('low','medium','high')", name=op.f("ck_crops_water_need")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crops")),
        sa.UniqueConstraint("slug", name=op.f("uq_crops_slug")),
    )
    op.create_table(
        "library_chunks",
        sa.Column("source_table", sa.String(length=20), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("lang", sa.String(length=2), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1024), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="approved", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_library_chunks")),
    )
    op.create_index(
        op.f("ix_library_chunks_source_id"), "library_chunks", ["source_id"], unique=False
    )
    op.create_table(
        "library_revisions",
        sa.Column("entity", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_library_revisions")),
        sa.UniqueConstraint("entity", "entity_id", "revision", name="entity_rev"),
    )
    op.create_table(
        "pests",
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name_en", sa.String(length=150), nullable=False),
        sa.Column("name_hi", sa.String(length=150), nullable=False),
        sa.Column("crop_ids", postgresql.ARRAY(sa.UUID()), server_default="{}", nullable=False),
        sa.Column("symptoms_en", sa.Text(), nullable=True),
        sa.Column("symptoms_hi", sa.Text(), nullable=True),
        sa.Column("months", postgresql.ARRAY(sa.Integer()), server_default="{}", nullable=False),
        sa.Column("recipe_ids", postgresql.ARRAY(sa.UUID()), server_default="{}", nullable=False),
        sa.Column("escalate_if", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("todo", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status in ('draft','in_review','approved','retired')", name=op.f("ck_pests_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pests")),
        sa.UniqueConstraint("slug", name=op.f("uq_pests_slug")),
    )
    op.create_table(
        "recipes",
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name_en", sa.String(length=100), nullable=False),
        sa.Column("name_hi", sa.String(length=100), nullable=False),
        sa.Column(
            "ingredients",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("per_area_sqm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("steps_en", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("steps_hi", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("ferment_days", sa.Integer(), nullable=True),
        sa.Column("shelf_life_days", sa.Integer(), nullable=True),
        sa.Column("apply_every_days", sa.Integer(), nullable=True),
        sa.Column("apply_method", sa.String(length=30), nullable=True),
        sa.Column("safety_notes_en", sa.Text(), nullable=True),
        sa.Column("safety_notes_hi", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("todo", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status in ('draft','in_review','approved','retired')", name=op.f("ck_recipes_status")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recipes")),
        sa.UniqueConstraint("slug", name=op.f("uq_recipes_slug")),
    )
    op.create_table(
        "companions",
        sa.Column("crop_a", sa.UUID(), nullable=False),
        sa.Column("crop_b", sa.UUID(), nullable=False),
        sa.Column("relation", sa.String(length=5), nullable=False),
        sa.Column("reason_en", sa.Text(), nullable=True),
        sa.Column("reason_hi", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint("relation in ('good','avoid')", name=op.f("ck_companions_relation")),
        sa.CheckConstraint(
            "status in ('draft','in_review','approved','retired')",
            name=op.f("ck_companions_status"),
        ),
        sa.CheckConstraint("crop_a < crop_b", name=op.f("ck_companions_ordered")),
        sa.ForeignKeyConstraint(
            ["crop_a"], ["crops.id"], name=op.f("fk_companions_crop_a_crops"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["crop_b"], ["crops.id"], name=op.f("fk_companions_crop_b_crops"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companions")),
        sa.UniqueConstraint("crop_a", "crop_b", name="pair"),
    )
    op.create_table(
        "crop_regional",
        sa.Column("crop_id", sa.UUID(), nullable=False),
        sa.Column("region_id", sa.UUID(), nullable=False),
        sa.Column(
            "sow_windows",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("price_mandi_paise_per_kg", sa.BigInteger(), nullable=True),
        sa.Column("price_direct_paise_per_kg", sa.BigInteger(), nullable=True),
        sa.Column("price_updated_on", sa.Date(), nullable=True),
        sa.Column(
            "agmarknet_commodity",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["crop_id"],
            ["crops.id"],
            name=op.f("fk_crop_regional_crop_id_crops"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["regions.id"], name=op.f("fk_crop_regional_region_id_regions")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crop_regional")),
        sa.UniqueConstraint("crop_id", "region_id", name="crop_region"),
    )
    op.create_table(
        "crop_varieties",
        sa.Column("crop_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("days_to_first_harvest", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status in ('draft','in_review','approved','retired')",
            name=op.f("ck_crop_varieties_status"),
        ),
        sa.ForeignKeyConstraint(
            ["crop_id"],
            ["crops.id"],
            name=op.f("fk_crop_varieties_crop_id_crops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crop_varieties")),
    )
    op.create_index(op.f("ix_crop_varieties_crop_id"), "crop_varieties", ["crop_id"], unique=False)
    op.create_table(
        "rules",
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("applies_to", sa.String(length=30), nullable=False),
        sa.Column("region_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=10), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("todo", postgresql.ARRAY(sa.String()), server_default="{}", nullable=False),
        sa.Column("submitted_by", sa.UUID(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "status in ('draft','in_review','approved','retired')", name=op.f("ck_rules_status")
        ),
        sa.ForeignKeyConstraint(
            ["region_id"], ["regions.id"], name=op.f("fk_rules_region_id_regions")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rules")),
        sa.UniqueConstraint("code", name=op.f("uq_rules_code")),
    )

    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "library.default_region", "value": "malwa",
         "description": "Region whose sow windows are required before a crop can be reviewed"},
        {"key": "library.self_approve_after_hours", "value": 24,
         "description": "Hours before the submitting agronomist may approve their own entry (spec 6)"},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key LIKE 'library.%'")
    op.drop_table("rules")
    op.drop_index(op.f("ix_crop_varieties_crop_id"), table_name="crop_varieties")
    op.drop_table("crop_varieties")
    op.drop_table("crop_regional")
    op.drop_table("companions")
    op.drop_table("recipes")
    op.drop_table("pests")
    op.drop_table("library_revisions")
    op.drop_index(op.f("ix_library_chunks_source_id"), table_name="library_chunks")
    op.drop_table("library_chunks")
    op.drop_table("crops")
