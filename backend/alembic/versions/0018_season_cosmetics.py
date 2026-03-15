"""0018 — Arena season exclusive cosmetic rewards

Revision ID: 0018
Revises: 0017
Create Date: 2026-02-28

Přidá:
  season_results.reward_title   — titul přidělený za sezónní umístění
  season_results.reward_frame   — portrait frame key přidělený za sezónní umístění
  characters.season_portrait_frame — aktivní sezónní frame (trvale odemčen výkonem)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(conn).get_columns(table)}
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "season_results", "reward_title"):
        op.add_column("season_results", sa.Column("reward_title", sa.String(64), nullable=True))

    if not _has_column(conn, "season_results", "reward_frame"):
        op.add_column("season_results", sa.Column("reward_frame", sa.String(32), nullable=True))

    if not _has_column(conn, "characters", "season_portrait_frame"):
        op.add_column("characters", sa.Column("season_portrait_frame", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("season_results", "reward_title")
    op.drop_column("season_results", "reward_frame")
    op.drop_column("characters", "season_portrait_frame")
