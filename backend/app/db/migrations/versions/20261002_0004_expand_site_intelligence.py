"""expand: site intelligence (M2b)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-02
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('geo_cache',
    sa.Column('cell_key', sa.String(length=30), nullable=False),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('cell_key', 'source', name=op.f('pk_geo_cache'))
    )
    op.create_table('groundwater_blocks',
    sa.Column('state', sa.String(length=60), nullable=False),
    sa.Column('district', sa.String(length=100), nullable=False),
    sa.Column('block', sa.String(length=100), nullable=True),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('assessed_year', sa.String(length=9), nullable=True),
    sa.Column('source_url', sa.Text(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.CheckConstraint("category in ('safe','semi_critical','critical','over_exploited','saline')", name=op.f('ck_groundwater_blocks_category')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_groundwater_blocks'))
    )
    op.create_table('district_regions',
    sa.Column('state', sa.String(length=60), nullable=False),
    sa.Column('district', sa.String(length=100), nullable=False),
    sa.Column('region_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['region_id'], ['regions.id'], name=op.f('fk_district_regions_region_id_regions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_district_regions')),
    sa.UniqueConstraint('state', 'district', name='district')
    )
    op.create_table('mandis',
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('district', sa.String(length=100), nullable=False),
    sa.Column('state', sa.String(length=60), nullable=False),
    sa.Column('lat', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('lng', sa.Numeric(precision=9, scale=6), nullable=True),
    sa.Column('region_id', sa.UUID(), nullable=True),
    sa.Column('geocode_tried', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['region_id'], ['regions.id'], name=op.f('fk_mandis_region_id_regions')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mandis')),
    sa.UniqueConstraint('name', 'district', 'state', name='market')
    )
    op.create_table('mandi_prices',
    sa.Column('mandi_id', sa.UUID(), nullable=False),
    sa.Column('commodity', sa.String(length=100), nullable=False),
    sa.Column('variety', sa.String(length=100), server_default='', nullable=False),
    sa.Column('crop_id', sa.UUID(), nullable=True),
    sa.Column('price_date', sa.Date(), nullable=False),
    sa.Column('min_paise', sa.BigInteger(), nullable=True),
    sa.Column('max_paise', sa.BigInteger(), nullable=True),
    sa.Column('modal_paise', sa.BigInteger(), nullable=True),
    sa.Column('unit', sa.String(length=10), server_default='quintal', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['mandi_id'], ['mandis.id'], name=op.f('fk_mandi_prices_mandi_id_mandis'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mandi_prices')),
    sa.UniqueConstraint('mandi_id', 'commodity', 'variety', 'price_date', name='price_day')
    )
    op.create_table('site_builds',
    sa.Column('farm_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('report', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.CheckConstraint("status in ('running','done','failed')", name=op.f('ck_site_builds_status')),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], name=op.f('fk_site_builds_farm_id_farms'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('farm_id', name=op.f('pk_site_builds'))
    )
    op.create_table('site_facts',
    sa.Column('farm_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=60), nullable=False),
    sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('unit', sa.String(length=20), nullable=True),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('method', sa.String(length=60), nullable=True),
    sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=False),
    sa.Column('attribution', sa.Text(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.String(length=10), server_default='derived', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status in ('derived','confirmed','edited','rejected')", name=op.f('ck_site_facts_status')),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], name=op.f('fk_site_facts_farm_id_farms'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_site_facts')),
    sa.UniqueConstraint('farm_id', 'key', 'source', name='farm_key_source')
    )
    op.create_index(op.f('ix_site_facts_farm_id'), 'site_facts', ['farm_id'], unique=False)

    # Settings (spec 17): budget, cache cell, thresholds. Values the spec does not give stay out.
    settings = sa.table(
        "settings", sa.column("key", sa.String), sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(settings, [
        {"key": "site.build_budget_s", "value": 20, "description": "Overall time budget for a site profile build (spec 17)"},
        {"key": "site.low_confidence", "value": 0.5, "description": "Facts below this confidence are asked as questions (spec 17)"},
        {"key": "site.default_state", "value": "Madhya Pradesh", "description": "State assumed when the farm has none"},
        {"key": "site.road_factor", "value": 1.3, "description": "Straight-line to road distance factor when OSRM is unavailable (decision)"},
        {"key": "site.nearest_mandis", "value": 3, "description": "Number of nearest mandis shown (spec 17)"},
        {"key": "site.reference_points", "value": [{"key": "indore", "name": "Indore", "lat": 22.7196, "lng": 75.8577}], "description": "Cities whose distance is shown (spec 17: Indore city)"},
        {"key": "site.mandi_ingest_max_pages", "value": 10, "description": "Pages of 1,000 rows fetched per ingest run"},
    ])


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key LIKE 'site.%'")
    op.drop_index(op.f('ix_site_facts_farm_id'), table_name='site_facts')
    op.drop_table('site_facts')
    op.drop_table('site_builds')
    op.drop_table('mandi_prices')
    op.drop_table('mandis')
    op.drop_table('district_regions')
    op.drop_table('groundwater_blocks')
    op.drop_table('geo_cache')
