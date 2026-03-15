"""0012 — Guild Wars: guild_wars + guild_war_attacks tables

Revision ID: 0012
Revises: 0011
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = set(inspect(conn).get_table_names())

    if "guild_wars" not in existing:
        op.create_table(
            "guild_wars",
            sa.Column("id",                 sa.Integer(), primary_key=True),
            sa.Column("attacker_guild_id",  sa.Integer(), sa.ForeignKey("guilds.id"), nullable=False),
            sa.Column("defender_guild_id",  sa.Integer(), sa.ForeignKey("guilds.id"), nullable=False),
            sa.Column("started_at",         sa.DateTime(), nullable=False),
            sa.Column("ends_at",            sa.DateTime(), nullable=False),
            sa.Column("status",             sa.String(16), nullable=False, server_default="active"),
            sa.Column("winner_guild_id",    sa.Integer(), sa.ForeignKey("guilds.id"), nullable=True),
            sa.Column("attacker_points",    sa.Integer(), nullable=False, server_default="0"),
            sa.Column("defender_points",    sa.Integer(), nullable=False, server_default="0"),
        )

    if "guild_war_attacks" not in existing:
        op.create_table(
            "guild_war_attacks",
            sa.Column("id",               sa.Integer(), primary_key=True),
            sa.Column("war_id",           sa.Integer(), sa.ForeignKey("guild_wars.id"), nullable=False),
            sa.Column("attacker_char_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("defender_char_id", sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("attacker_won",     sa.Boolean(), nullable=False),
            sa.Column("points_earned",    sa.Integer(), nullable=False, server_default="0"),
            sa.Column("attacked_at",      sa.DateTime(), nullable=False),
            sa.Column("events_json",      sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("guild_war_attacks")
    op.drop_table("guild_wars")
