"""balance_alerts table

Revision ID: 0033
Revises: 0032
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "balance_alerts" not in inspector.get_table_names():
        op.create_table(
            "balance_alerts",
            sa.Column("id",          sa.Integer(),  nullable=False, primary_key=True),
            sa.Column("alert_type",  sa.String(32), nullable=False),
            sa.Column("severity",    sa.String(16), nullable=False, server_default="warning"),
            sa.Column("title",       sa.String(128), nullable=False),
            sa.Column("detail",      sa.Text(),     nullable=False, server_default=""),
            sa.Column("detected_at", sa.DateTime(), nullable=False),
            sa.Column("resolved",    sa.Boolean(),  nullable=False, server_default="0"),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_balance_alerts_alert_type", "balance_alerts", ["alert_type"])


def downgrade() -> None:
    op.drop_index("ix_balance_alerts_alert_type", table_name="balance_alerts")
    op.drop_table("balance_alerts")
