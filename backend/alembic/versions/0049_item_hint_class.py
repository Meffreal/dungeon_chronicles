"""items: přidej hint_class

Revision ID: 0049
Revises: 0048
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0049'
down_revision = '0048'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('items')]
    if 'hint_class' not in cols:
        op.add_column(
            'items',
            sa.Column('hint_class', sa.String(16), nullable=True),
        )


def downgrade():
    op.drop_column('items', 'hint_class')
