"""daily_quest_rotation — denní rotace questů pro každého hráče

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-27
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_quest_rotations",
        sa.Column("id",           sa.Integer(),  nullable=False, autoincrement=True),
        sa.Column("character_id", sa.Integer(),  nullable=False),
        sa.Column("date",         sa.String(10), nullable=False),
        sa.Column("quest_ids",    sa.Text(),     nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_rot_char_date", "daily_quest_rotations", ["character_id", "date"])


def downgrade() -> None:
    op.drop_index("ix_daily_rot_char_date", table_name="daily_quest_rotations")
    op.drop_table("daily_quest_rotations")
