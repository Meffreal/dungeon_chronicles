"""0026 — SeasonResult recap_shown flag

Revision ID: 0026
Revises: 0025
Create Date: 2026-03-06

Přidá na season_results:
  recap_shown  BOOLEAN DEFAULT FALSE — hráč viděl sezónní recap modal
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision      = '0026'
down_revision = '0025'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns("season_results")]

    if "recap_shown" not in cols:
        op.add_column("season_results", sa.Column(
            "recap_shown", sa.Boolean(), nullable=False, server_default="0"
        ))


def downgrade() -> None:
    op.drop_column("season_results", "recap_shown")
