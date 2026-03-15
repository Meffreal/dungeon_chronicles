"""0025 — Season theme columns

Revision ID: 0025
Revises: 0024
Create Date: 2026-03-06

Přidá na seasons:
  theme_name  VARCHAR(64) NULL — název tématu sezóny
  theme_lore  TEXT NULL        — lore text sezóny (2-3 věty)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision      = '0025'
down_revision = '0024'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns("seasons")]

    if "theme_name" not in cols:
        op.add_column("seasons", sa.Column(
            "theme_name", sa.String(64), nullable=True
        ))
    if "theme_lore" not in cols:
        op.add_column("seasons", sa.Column(
            "theme_lore", sa.Text(), nullable=True
        ))


def downgrade() -> None:
    op.drop_column("seasons", "theme_lore")
    op.drop_column("seasons", "theme_name")
