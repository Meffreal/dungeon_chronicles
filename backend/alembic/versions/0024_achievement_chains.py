"""0024 — Achievement chain completions table

Revision ID: 0024
Revises: 0023
Create Date: 2026-03-06

Přidá tabulku player_chain_completions pro tracking dokončených chainů.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision      = '0024'
down_revision = '0023'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing = insp.get_table_names()

    if "player_chain_completions" not in existing:
        op.create_table(
            "player_chain_completions",
            sa.Column("id",           sa.Integer(),     nullable=False, primary_key=True),
            sa.Column("character_id", sa.Integer(),     sa.ForeignKey("characters.id"), nullable=False),
            sa.Column("chain_id",     sa.String(64),    nullable=False),
            sa.Column("completed_at", sa.DateTime(),    nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("player_chain_completions")
