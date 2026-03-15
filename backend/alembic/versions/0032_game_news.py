"""game_news table

Revision ID: 0032
Revises: 0031
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    if "game_news" not in inspector.get_table_names():
        op.create_table(
            "game_news",
            sa.Column("id",           sa.Integer(),     nullable=False, primary_key=True),
            sa.Column("title",        sa.String(120),   nullable=False),
            sa.Column("body",         sa.Text(),        nullable=False),
            sa.Column("news_type",    sa.String(20),    nullable=False, server_default="info"),
            sa.Column("published_at", sa.DateTime(),    nullable=False),
            sa.Column("expires_at",   sa.DateTime(),    nullable=True),
            sa.Column("is_active",    sa.Boolean(),     nullable=False, server_default="1"),
            sa.Column("author",       sa.String(64),    nullable=True),
        )


def downgrade() -> None:
    op.drop_table("game_news")
