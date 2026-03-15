"""legacy pending columns on inventory

Revision ID: 0040
Revises: 0039
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0040'
down_revision = '0039'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('inventory')]
    if 'is_legacy_pending' not in cols:
        op.add_column('inventory', sa.Column('is_legacy_pending', sa.Boolean(), nullable=True, server_default='0'))
    if 'legacy_owner_user_id' not in cols:
        op.add_column('inventory', sa.Column('legacy_owner_user_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('inventory', 'legacy_owner_user_id')
    op.drop_column('inventory', 'is_legacy_pending')
