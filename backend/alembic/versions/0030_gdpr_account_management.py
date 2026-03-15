"""0030 — GDPR account management: is_deleted, deleted_at, anonymized na users

Revision ID: 0030
Revises: 0029
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    user_cols = [c["name"] for c in inspector.get_columns("users")]

    if "is_deleted" not in user_cols:
        op.add_column(
            "users",
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
        )
    if "deleted_at" not in user_cols:
        op.add_column(
            "users",
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
    if "anonymized" not in user_cols:
        op.add_column(
            "users",
            sa.Column("anonymized", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade():
    op.drop_column("users", "anonymized")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "is_deleted")
