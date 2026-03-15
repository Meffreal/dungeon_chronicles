"""0020 — Prestige soft cap: portrait frame column

Revision ID: 0020
Revises: 0019
Create Date: 2026-02-28

Přidá:
  characters.prestige_portrait_frame — klíč aktivního prestige portrait frame
                                        (odemyká se za každý prestige level 1-10)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(conn).get_columns(table)}
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "characters", "prestige_portrait_frame"):
        op.add_column("characters", sa.Column("prestige_portrait_frame", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "prestige_portrait_frame")
