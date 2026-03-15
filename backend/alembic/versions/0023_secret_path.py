"""0023 — Dungeon secret path branching

Revision ID: 0023
Revises: 0022
Create Date: 2026-03-06

Přidá na dungeon_runs:
  secret_path_offered  BOOL DEFAULT FALSE — roll proběhl a tajný průchod byl nabídnut
  secret_path_taken    BOOL DEFAULT FALSE — hráč přijal tajný průchod
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision      = '0023'
down_revision = '0022'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c["name"] for c in insp.get_columns("dungeon_runs")]

    if "secret_path_offered" not in cols:
        op.add_column("dungeon_runs", sa.Column(
            "secret_path_offered", sa.Boolean(), nullable=False, server_default="0"
        ))
    if "secret_path_taken" not in cols:
        op.add_column("dungeon_runs", sa.Column(
            "secret_path_taken", sa.Boolean(), nullable=False, server_default="0"
        ))


def downgrade() -> None:
    op.drop_column("dungeon_runs", "secret_path_taken")
    op.drop_column("dungeon_runs", "secret_path_offered")
