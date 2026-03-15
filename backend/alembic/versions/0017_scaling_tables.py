"""0017 — Scaling tables: cron_jobs + disabled_quests

Revision ID: 0017
Revises: 0016
Create Date: 2026-02-28

Tyto tabulky zajišťují multi-instance bezpečný provoz:
  cron_jobs      — distributed lock pro background tasky (ELO decay atd.)
  disabled_quests — DB-backed admin content toggle (nahrazuje in-memory set)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_tables = set(inspect(conn).get_table_names())

    if "cron_jobs" not in existing_tables:
        op.create_table(
            "cron_jobs",
            sa.Column("name",        sa.String(64),  primary_key=True),
            sa.Column("last_run_at", sa.DateTime(),  nullable=True),
            sa.Column("run_count",   sa.Integer(),   nullable=False, server_default="0"),
            sa.Column("locked_by",   sa.String(64),  nullable=True),
        )

    if "disabled_quests" not in existing_tables:
        op.create_table(
            "disabled_quests",
            sa.Column("quest_id",    sa.Integer(),   primary_key=True),
            sa.Column("disabled_at", sa.DateTime(),  nullable=True),
        )


def downgrade() -> None:
    op.drop_table("disabled_quests")
    op.drop_table("cron_jobs")
