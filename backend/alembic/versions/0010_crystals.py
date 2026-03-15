"""0010 — Crystal currency: add fields to characters + crystal_transactions table

Revision ID: 0010
Revises: 0009
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())
    char_cols = {col["name"] for col in inspector.get_columns("characters")}

    # Přidej crystal pole do tabulky characters (pokud chybí)
    if "crystals" not in char_cols:
        op.add_column("characters", sa.Column("crystals", sa.Integer(), nullable=False, server_default="0"))
    if "crystal_name_color" not in char_cols:
        op.add_column("characters", sa.Column("crystal_name_color", sa.String(20), nullable=True))
    if "crystal_portrait_frame" not in char_cols:
        op.add_column("characters", sa.Column("crystal_portrait_frame", sa.String(32), nullable=True))
    if "crystal_xp_boost_until" not in char_cols:
        op.add_column("characters", sa.Column("crystal_xp_boost_until", sa.DateTime(), nullable=True))

    # Nová transakční tabulka (pokud neexistuje)
    if "crystal_transactions" not in existing_tables:
        op.create_table(
            "crystal_transactions",
            sa.Column("id",            sa.Integer(),    primary_key=True),
            sa.Column("character_id",  sa.Integer(),    sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("amount",        sa.Integer(),    nullable=False),
            sa.Column("reason",        sa.String(64),   nullable=False),
            sa.Column("timestamp",     sa.DateTime(),   nullable=False),
            sa.Column("balance_after", sa.Integer(),    nullable=False),
        )


def downgrade() -> None:
    op.drop_table("crystal_transactions")
    op.drop_column("characters", "crystal_xp_boost_until")
    op.drop_column("characters", "crystal_portrait_frame")
    op.drop_column("characters", "crystal_name_color")
    op.drop_column("characters", "crystals")
