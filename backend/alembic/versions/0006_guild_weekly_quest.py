"""0006 — Guild Weekly Quest tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names())

    if "guild_weekly_quests" not in existing:
        op.create_table(
            "guild_weekly_quests",
            sa.Column("id",           sa.Integer(),    primary_key=True),
            sa.Column("guild_id",     sa.Integer(),    sa.ForeignKey("guilds.id"), nullable=False),
            sa.Column("week_start",   sa.DateTime(),   nullable=False),
            sa.Column("goal_type",    sa.String(32),   nullable=False),
            sa.Column("goal_target",  sa.Integer(),    nullable=False),
            sa.Column("progress",     sa.Integer(),    nullable=False, server_default="0"),
            sa.Column("is_completed", sa.Boolean(),    nullable=False, server_default="0"),
            sa.Column("reward_gold",  sa.Integer(),    nullable=False, server_default="0"),
            sa.Column("completed_at", sa.DateTime(),   nullable=True),
        )

    if "guild_weekly_contribs" not in existing:
        op.create_table(
            "guild_weekly_contribs",
            sa.Column("id",           sa.Integer(), primary_key=True),
            sa.Column("quest_id",     sa.Integer(), sa.ForeignKey("guild_weekly_quests.id"), nullable=False),
            sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("contribution", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_table("guild_weekly_contribs")
    op.drop_table("guild_weekly_quests")
