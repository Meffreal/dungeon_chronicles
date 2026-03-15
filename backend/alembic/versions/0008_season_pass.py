"""0008 — Season Pass tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names())

    if "season_passes" not in existing:
        op.create_table(
            "season_passes",
            sa.Column("id",          sa.Integer(),    primary_key=True),
            sa.Column("season_num",  sa.Integer(),    nullable=False, server_default="1"),
            sa.Column("name",        sa.String(64),   nullable=False),
            sa.Column("start_date",  sa.DateTime(),   nullable=False),
            sa.Column("end_date",    sa.DateTime(),   nullable=False),
            sa.Column("is_active",   sa.Boolean(),    nullable=False, server_default="1"),
        )

    if "season_pass_progress" not in existing:
        op.create_table(
            "season_pass_progress",
            sa.Column("id",            sa.Integer(), primary_key=True),
            sa.Column("character_id",  sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("season_id",     sa.Integer(), sa.ForeignKey("season_passes.id"), nullable=False),
            sa.Column("season_xp",     sa.Integer(), nullable=False, server_default="0"),
            sa.Column("claimed_tiers", sa.Text(),    nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    op.drop_table("season_pass_progress")
    op.drop_table("season_passes")
