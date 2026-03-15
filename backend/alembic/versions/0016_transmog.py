"""0016 — Transmog systém: transmog_slots tabulka

Revision ID: 0016
Revises: 0015
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = set(inspect(conn).get_table_names())

    if "transmog_slots" not in existing_tables:
        op.create_table(
            "transmog_slots",
            sa.Column("id",               sa.Integer(), primary_key=True),
            sa.Column("character_id",     sa.Integer(), sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("slot",             sa.String(16), nullable=False),
            sa.Column("cosmetic_item_id", sa.Integer(), sa.ForeignKey("items.id"), nullable=False),
            sa.Column("applied_at",       sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("transmog_slots")
