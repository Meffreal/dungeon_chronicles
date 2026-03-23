"""0053 dungeon boss progress

Revision ID: 0053
Revises: 0052
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # ── Table: dungeon_boss_progress ──────────────────────────────────────────
    if "dungeon_boss_progress" not in existing_tables:
        op.create_table(
            "dungeon_boss_progress",
            sa.Column("id",                    sa.Integer, primary_key=True),
            sa.Column("character_id",          sa.Integer, sa.ForeignKey("characters.id"), nullable=False, index=True),
            sa.Column("dungeon_key",            sa.String(32), nullable=False),
            sa.Column("highest_boss_defeated", sa.Integer, default=0, nullable=False, server_default="0"),
            sa.Column("total_kills",           sa.Integer, default=0, nullable=False, server_default="0"),
            sa.Column("last_fight_at",         sa.DateTime, nullable=True),
            sa.Column("last_combat_log_json",  sa.Text, nullable=True),
        )

    # ── Column: characters.dungeon_cooldown_until ─────────────────────────────
    chars_cols = [c["name"] for c in inspector.get_columns("characters")]
    if "dungeon_cooldown_until" not in chars_cols:
        op.add_column(
            "characters",
            sa.Column("dungeon_cooldown_until", sa.DateTime, nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "dungeon_boss_progress" in inspector.get_table_names():
        op.drop_table("dungeon_boss_progress")

    chars_cols = [c["name"] for c in inspector.get_columns("characters")]
    if "dungeon_cooldown_until" in chars_cols:
        op.drop_column("characters", "dungeon_cooldown_until")
