"""gold_transactions — economy audit log tabulka

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-27
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gold_transactions",
        sa.Column("id",            sa.Integer(),     nullable=False, autoincrement=True),
        sa.Column("character_id",  sa.Integer(),     nullable=False),
        sa.Column("amount",        sa.Integer(),     nullable=False),
        sa.Column("reason",        sa.String(32),    nullable=False),
        sa.Column("balance_after", sa.Integer(),     nullable=False),
        sa.Column("timestamp",     sa.DateTime(),    nullable=True),
        sa.Column("detail",        sa.Text(),        nullable=True),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gold_tx_character_id", "gold_transactions", ["character_id"])
    op.create_index("ix_gold_tx_timestamp",    "gold_transactions", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_gold_tx_timestamp",    "gold_transactions")
    op.drop_index("ix_gold_tx_character_id", "gold_transactions")
    op.drop_table("gold_transactions")
