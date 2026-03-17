"""market_listings: přidej upgrade_level

Revision ID: 0047
Revises: 0046
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0047'
down_revision = '0046'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('market_listings')]
    if 'upgrade_level' not in cols:
        op.add_column(
            'market_listings',
            sa.Column('upgrade_level', sa.Integer(), server_default='0', nullable=False),
        )


def downgrade():
    op.drop_column('market_listings', 'upgrade_level')
