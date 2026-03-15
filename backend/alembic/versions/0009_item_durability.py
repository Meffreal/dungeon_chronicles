"""0009 — Add durability column to inventory table

Revision ID: 0009
Revises: 0008
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_cols = {col["name"] for col in inspect(conn).get_columns("inventory")}

    if "durability" not in existing_cols:
        op.add_column(
            "inventory",
            sa.Column("durability", sa.Integer(), nullable=False, server_default="100"),
        )


def downgrade() -> None:
    op.drop_column("inventory", "durability")
