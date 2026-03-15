"""0014 — World Events: world_events + world_event_contribs + world_event_claims

Revision ID: 0014
Revises: 0013
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = set(inspect(conn).get_table_names())

    if "world_events" not in existing_tables:
        op.create_table(
            "world_events",
            sa.Column("id",               sa.Integer(), primary_key=True),
            sa.Column("name",             sa.String(128), nullable=False),
            sa.Column("description",      sa.Text(), nullable=True),
            sa.Column("event_type",       sa.String(32), nullable=False),
            sa.Column("goal",             sa.Integer(), nullable=False),
            sa.Column("current_progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("starts_at",        sa.DateTime(), nullable=False),
            sa.Column("ends_at",          sa.DateTime(), nullable=False),
            sa.Column("is_active",        sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_completed",     sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("reward_gold",      sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reward_crystals",  sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reward_title",     sa.String(64), nullable=True),
        )

    if "world_event_contribs" not in existing_tables:
        op.create_table(
            "world_event_contribs",
            sa.Column("id",              sa.Integer(), primary_key=True),
            sa.Column("event_id",        sa.Integer(), sa.ForeignKey("world_events.id"), nullable=False),
            sa.Column("character_id",    sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("contribution",    sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_contrib_at", sa.DateTime(), nullable=False),
        )

    if "world_event_claims" not in existing_tables:
        op.create_table(
            "world_event_claims",
            sa.Column("id",                sa.Integer(), primary_key=True),
            sa.Column("event_id",          sa.Integer(), sa.ForeignKey("world_events.id"), nullable=False),
            sa.Column("character_id",      sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("claimed_at",        sa.DateTime(), nullable=False),
            sa.Column("gold_received",     sa.Integer(), nullable=False, server_default="0"),
            sa.Column("crystals_received", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_table("world_event_claims")
    op.drop_table("world_event_contribs")
    op.drop_table("world_events")
