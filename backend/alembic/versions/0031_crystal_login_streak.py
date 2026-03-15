"""0031_crystal_login_streak — login streak sloupce na characters

Revision ID: 0031
Revises: 0030
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    cols = [c["name"] for c in insp.get_columns("characters")]

    if "login_streak" not in cols:
        op.add_column(
            "characters",
            sa.Column("login_streak", sa.Integer(), nullable=False, server_default="0"),
        )
    if "last_login_date" not in cols:
        op.add_column(
            "characters",
            sa.Column("last_login_date", sa.String(10), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("characters", "last_login_date")
    op.drop_column("characters", "login_streak")
