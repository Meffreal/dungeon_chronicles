"""0019 — Onboarding flag + arena gold daily cap

Revision ID: 0019
Revises: 0018
Create Date: 2026-02-28

Přidá:
  characters.onboarding_completed  — boolean, zda hráč dokončil úvodní průvodce
  characters.arena_gold_today      — kolik goldu bylo dnes vydělano v aréně (reset v 00:00 UTC)
  characters.arena_gold_date       — datum posledního arena gold restartu
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(conn).get_columns(table)}
    return column in cols


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "characters", "onboarding_completed"):
        op.add_column("characters", sa.Column("onboarding_completed", sa.Integer, nullable=False, server_default="0"))

    if not _has_column(conn, "characters", "arena_gold_today"):
        op.add_column("characters", sa.Column("arena_gold_today", sa.Integer, nullable=False, server_default="0"))

    if not _has_column(conn, "characters", "arena_gold_date"):
        op.add_column("characters", sa.Column("arena_gold_date", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "onboarding_completed")
    op.drop_column("characters", "arena_gold_today")
    op.drop_column("characters", "arena_gold_date")
