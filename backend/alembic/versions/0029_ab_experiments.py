"""0029 — A/B testing framework: experiment_group na characters, tabulka experiments

Revision ID: 0029
Revises: 0028
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # ── 1. experiment_group na characters (0–9, náhodně přiřazeno při vytvoření) ──
    char_cols = [c["name"] for c in inspector.get_columns("characters")]
    if "experiment_group" not in char_cols:
        op.add_column(
            "characters",
            sa.Column("experiment_group", sa.Integer(), nullable=False,
                      server_default="0"),
        )

    # ── 2. Tabulka experiments ───────────────────────────────────────────────
    existing_tables = inspector.get_table_names()
    if "experiments" not in existing_tables:
        op.create_table(
            "experiments",
            sa.Column("id",            sa.Integer(),  primary_key=True),
            sa.Column("name",          sa.String(64), nullable=False),
            sa.Column("description",   sa.Text(),     nullable=False, server_default=""),
            sa.Column("group_start",   sa.Integer(),  nullable=False, server_default="0"),
            sa.Column("group_end",     sa.Integer(),  nullable=False, server_default="4"),
            sa.Column("override_json", sa.Text(),     nullable=False, server_default="{}"),
            sa.Column("is_active",     sa.Boolean(),  nullable=False, server_default="1"),
            sa.Column("created_at",    sa.DateTime(), server_default=sa.text("(datetime('now'))")),
        )


def downgrade():
    op.drop_table("experiments")
    op.drop_column("characters", "experiment_group")
