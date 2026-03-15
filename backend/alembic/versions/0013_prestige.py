"""0013 — Prestige systém: prestige_level na characters + prestige_log tabulka

Revision ID: 0013
Revises: 0012
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = set(inspect(conn).get_table_names())
    existing_cols   = {col["name"] for col in inspect(conn).get_columns("characters")}

    if "prestige_level" not in existing_cols:
        op.add_column(
            "characters",
            sa.Column("prestige_level", sa.Integer(), nullable=False, server_default="0"),
        )

    if "prestige_log" not in existing_tables:
        op.create_table(
            "prestige_log",
            sa.Column("id",              sa.Integer(), primary_key=True),
            sa.Column("character_id",    sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("prestige_level",  sa.Integer(), nullable=False),
            sa.Column("prestiged_at",    sa.DateTime(), nullable=False),
            sa.Column("reward_crystals", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("awarded_title",   sa.String(64), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("prestige_log")
    op.drop_column("characters", "prestige_level")
