"""0015 — Dungeon Modifiers: weekly_dungeon_modifiers tabulka

Revision ID: 0015
Revises: 0014
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = set(inspect(conn).get_table_names())

    if "weekly_dungeon_modifiers" not in existing_tables:
        op.create_table(
            "weekly_dungeon_modifiers",
            sa.Column("id",           sa.Integer(),    primary_key=True),
            sa.Column("modifier_key", sa.String(32),   nullable=False),
            sa.Column("week_start",   sa.DateTime(),   nullable=False),
            sa.Column("week_end",     sa.DateTime(),   nullable=False),
            sa.Column("is_active",    sa.Boolean(),    nullable=False, server_default="1"),
        )


def downgrade() -> None:
    op.drop_table("weekly_dungeon_modifiers")
