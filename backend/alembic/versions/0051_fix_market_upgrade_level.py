"""market_listings: fix chybějící sloupec upgrade_level

Migration 0047 se kvůli MultipleHeads konfliktu neaplikovala správně —
upgrade_level v produkční DB chybí. Tato migrace to opravuje idempotentně.

Revision ID: 0051
Revises: 0050
Create Date: 2026-03-18
"""
from alembic import op
from sqlalchemy import inspect, Column, Integer

revision = '0051'
down_revision = '0050'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('market_listings')]
    if 'upgrade_level' not in cols:
        op.add_column(
            'market_listings',
            Column('upgrade_level', Integer, server_default='0', nullable=False),
        )


def downgrade():
    pass
