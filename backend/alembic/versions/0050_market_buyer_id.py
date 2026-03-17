"""market_listings: přidej buyer_id

Revision ID: 0050
Revises: 0049
Create Date: 2026-03-17
"""
from alembic import op
from sqlalchemy import inspect, Column, Integer, ForeignKey

revision = '0050'
down_revision = '0049'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('market_listings')]
    if 'buyer_id' not in cols:
        op.add_column(
            'market_listings',
            Column('buyer_id', Integer, ForeignKey('characters.id'), nullable=True),
        )


def downgrade():
    pass
