"""expand: foundation tables (M0)

Revision ID: 0001
Revises:
Create Date: 2026-09-30
Phase: expand
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = pg.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ---- platform (app.core) ----
    op.create_table(
        "settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", pg.JSONB, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("updated_by", UUID),
        sa.Column("updated_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("actor_id", UUID),
        sa.Column("entity", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("before", pg.JSONB),
        sa.Column("after", pg.JSONB),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_entity", "audit_log", ["entity", "entity_id"])
    op.create_table(
        "outbox",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", TS),
        sa.Column("delivered_to", pg.ARRAY(sa.String), server_default="{}", nullable=False),
        sa.Column("attempts", sa.Integer, server_default="0", nullable=False),
        sa.Column("last_error", sa.Text),
        sa.Column("next_attempt_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["next_attempt_at"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )
    op.create_table(
        "jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("run_key", sa.String(200), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer, server_default="1", nullable=False),
        sa.Column("last_error", sa.Text),
        sa.Column("run_at", TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "regions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_hi", sa.String(100), nullable=False),
        *_ts(),
    )

    # ---- identity ----
    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("phone", sa.String(20), unique=True),
        sa.Column("name", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("language", sa.String(2), server_default="hi", nullable=False),
        sa.Column("unit_pref", sa.String(5), server_default="sqft", nullable=False),
        sa.Column("bigha_sqft", sa.Numeric),
        sa.Column("is_admin", sa.Boolean, server_default="false", nullable=False),
        sa.Column("is_agronomist", sa.Boolean, server_default="false", nullable=False),
        sa.Column("keycloak_sub", sa.String(64), unique=True),
        sa.Column("session_version", sa.Integer, server_default="1", nullable=False),
        *_ts(),
        sa.Column("deleted_at", TS),
        sa.CheckConstraint("language in ('en','hi')", name="language"),
        sa.CheckConstraint("unit_pref in ('sqft','acre','bigha','sqm')", name="unit_pref"),
        sa.CheckConstraint("bigha_sqft is null or bigha_sqft > 0", name="bigha_sqft"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "channel_accounts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("opted_out", sa.Boolean, server_default="false", nullable=False),
        *_ts(),
        sa.UniqueConstraint("channel", "external_id", name="channel_external"),
    )
    op.create_table(
        "login_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("used_at", TS),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
    )

    # ---- farms ----
    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        *_ts(),
    )
    op.create_table(
        "farms",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("site_type", sa.String(10)),
        sa.Column("district", sa.String(100)),
        sa.Column("village", sa.String(100)),
        sa.Column("lat", sa.Numeric(9, 6)),
        sa.Column("lng", sa.Numeric(9, 6)),
        sa.Column("goal", sa.String(10)),
        sa.Column("budget_setup_paise", sa.BigInteger),
        sa.Column("budget_monthly_paise", sa.BigInteger),
        sa.Column("labour", sa.String(10)),
        sa.Column("water_source", sa.String(10)),
        sa.Column("water_summer_lpd", sa.Integer),
        sa.Column("electricity", sa.Boolean),
        sa.Column("livestock", sa.Boolean, server_default="false", nullable=False),
        sa.Column("region_id", UUID, sa.ForeignKey("regions.id")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id")),
        sa.Column("metadata", pg.JSONB, server_default="{}", nullable=False),
        sa.Column("created_by", UUID),
        *_ts(),
        sa.Column("deleted_at", TS),
        sa.CheckConstraint("site_type in ('ground','terrace')", name="site_type"),
        sa.CheckConstraint("goal in ('home_food','income','both')", name="goal"),
        sa.CheckConstraint("labour in ('self','family','caretaker','mixed')", name="labour"),
        sa.CheckConstraint(
            "water_source in ('bore','well','canal','municipal','rain_only')", name="water_source"
        ),
        sa.CheckConstraint("budget_setup_paise >= 0", name="budget_setup"),
        sa.CheckConstraint("budget_monthly_paise >= 0", name="budget_monthly"),
    )
    op.create_table(
        "farm_members",
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("caretaker_sees_money", sa.Boolean, server_default="false", nullable=False),
        *_ts(),
        sa.CheckConstraint("role in ('owner','caretaker')", name="role"),
    )
    op.create_index("ix_farm_members_user_id", "farm_members", ["user_id"])
    op.create_table(
        "invites",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("farm_id", UUID, sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("accepted_at", TS),
        sa.Column("created_by", UUID),
        sa.Column("created_at", TS, server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role in ('caretaker')", name="role"),
    )
    op.create_index("ix_invites_farm_id", "invites", ["farm_id"])

    # ---- seed data ----
    op.execute(
        "INSERT INTO regions (id, slug, name_en, name_hi) "
        "VALUES (gen_random_uuid(), 'malwa', 'Malwa', 'मालवा')"
    )
    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value", pg.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        settings,
        [
            {
                "key": "auth.link_ttl_minutes",
                "value": 15,
                "description": "Caretaker login link lifetime (spec 14)",
            },
            {
                "key": "auth.link_rate_limit",
                "value": {"max": 3, "window_minutes": 10, "max_per_ip": 10},
                "description": "Link requests per phone (spec 12) and per IP (decision)",
            },
            {
                "key": "auth.caretaker_session_days",
                "value": 30,
                "description": "Caretaker session lifetime; spec silent, see decisions.md",
            },
            {
                "key": "invites.ttl_days",
                "value": 7,
                "description": "Invite link lifetime; spec silent, see decisions.md",
            },
        ],
    )


def downgrade() -> None:
    for table in (
        "invites",
        "farm_members",
        "farms",
        "organizations",
        "login_links",
        "channel_accounts",
        "users",
        "regions",
        "jobs",
        "outbox",
        "audit_log",
        "settings",
    ):
        op.drop_table(table)
