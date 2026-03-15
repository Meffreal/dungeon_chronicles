"""0011 — Add subclass column to characters

Revision ID: 0011
Revises: 0010
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_cols = {col["name"] for col in inspect(conn).get_columns("characters")}

    if "subclass" not in existing_cols:
        op.add_column(
            "characters",
            sa.Column("subclass", sa.String(32), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("characters", "subclass")
