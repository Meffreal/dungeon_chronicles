"""0034 — Quest is_daily: pridani sloupce is_daily do tabulky quests

Revision ID: 0034
Revises: 0033
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    cols = [c["name"] for c in inspector.get_columns("quests")]

    if "is_daily" not in cols:
        op.add_column(
            "quests",
            sa.Column("is_daily", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade():
    op.drop_column("quests", "is_daily")
