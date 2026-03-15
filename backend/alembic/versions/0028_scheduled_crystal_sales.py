"""0028 — Tabulka naplánovaných Crystal shop slev

Revision ID: 0028
Revises: 0027
Create Date: 2026-03-07
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision    = '0028'
down_revision = '0027'
branch_labels = None
depends_on  = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    if 'scheduled_crystal_sales' not in insp.get_table_names():
        op.create_table(
            'scheduled_crystal_sales',
            sa.Column('id',            sa.Integer,     primary_key=True),
            sa.Column('item_key',      sa.String(64),  nullable=False),
            sa.Column('original_cost', sa.Integer,     nullable=False),
            sa.Column('sale_cost',     sa.Integer,     nullable=False),
            sa.Column('starts_at',     sa.DateTime,    nullable=False),
            sa.Column('ends_at',       sa.DateTime,    nullable=False),
            sa.Column('label',         sa.String(64),  nullable=True),
        )


def downgrade():
    op.drop_table('scheduled_crystal_sales')
