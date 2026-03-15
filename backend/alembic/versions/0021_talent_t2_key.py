"""0021 — Talent Tier 2: talent_t2_key column

Revision ID: 0021
Revises: 0020
Create Date: 2026-03-01

Přidá:
  characters.talent_t2_key — klíč zvoleného T2 talentu (irreverzibilní volba na levelu 25)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(conn).get_columns(table)}
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "characters", "talent_t2_key"):
        op.add_column("characters", sa.Column("talent_t2_key", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "talent_t2_key")
