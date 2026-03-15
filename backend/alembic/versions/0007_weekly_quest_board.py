"""0007 — Weekly Quest Board (individuální)

Revision ID: 0007
Revises: 0006
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names())

    if "weekly_quest_progress" not in existing:
        op.create_table(
            "weekly_quest_progress",
            sa.Column("id",           sa.Integer(),  primary_key=True),
            sa.Column("character_id", sa.Integer(),  sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("week_start",   sa.DateTime(), nullable=False),
            sa.Column("slot",         sa.Integer(),  nullable=False),
            sa.Column("goal_type",    sa.String(32), nullable=False),
            sa.Column("goal_target",  sa.Integer(),  nullable=False),
            sa.Column("progress",     sa.Integer(),  nullable=False, server_default="0"),
            sa.Column("is_completed", sa.Boolean(),  nullable=False, server_default="0"),
            sa.Column("reward_xp",    sa.Integer(),  nullable=False, server_default="0"),
            sa.Column("reward_gold",  sa.Integer(),  nullable=False, server_default="0"),
            sa.Column("claimed",      sa.Boolean(),  nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_table("weekly_quest_progress")
