"""expand: Madhya Pradesh and India regions, with a lookup order for crop sowing windows

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-07
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO regions (id, slug, name_en, name_hi) VALUES "
        "(gen_random_uuid(), 'madhya-pradesh', 'Madhya Pradesh', 'मध्य प्रदेश'), "
        "(gen_random_uuid(), 'india', 'India (general)', 'भारत (सामान्य)')"
    )
    # Every window stored so far came from Tamil Nadu pages (TNAU), kept under 'malwa' only until a
    # local source turned up. Move them to 'india' so 'malwa' means Malwa data only.
    op.execute(
        "UPDATE crop_regional SET region_id = (SELECT id FROM regions WHERE slug = 'india') "
        "WHERE region_id = (SELECT id FROM regions WHERE slug = 'malwa')"
    )
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
                "key": "library.region_fallback",
                "value": ["madhya-pradesh", "india"],
                "description": "Regions tried after the farm's own region when a crop has no sowing window "
                "there (decision 2026-10-07: all-India data, Madhya Pradesh first)",
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'library.region_fallback'")
    op.execute(
        "UPDATE crop_regional SET region_id = (SELECT id FROM regions WHERE slug = 'malwa') "
        "WHERE region_id = (SELECT id FROM regions WHERE slug = 'india')"
    )
    op.execute("DELETE FROM regions WHERE slug IN ('madhya-pradesh', 'india')")
