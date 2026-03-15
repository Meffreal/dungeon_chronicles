"""faction system — add characters.faction column and faction_reputation table

Revision ID: 0042
Revises: 0041
Create Date: 2026-03-15
"""
from alembic import op
from sqlalchemy import inspect, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

revision = '0042'
down_revision = '0041'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1. Přidání sloupce faction do tabulky characters (idempotentní)
    cols = [c['name'] for c in inspector.get_columns('characters')]
    if 'faction' not in cols:
        op.add_column('characters', Column('faction', String(32), nullable=True))

    # 2. Vytvoření tabulky faction_reputation (idempotentní)
    if 'faction_reputation' not in inspector.get_table_names():
        op.create_table(
            'faction_reputation',
            Column('id', Integer, primary_key=True),
            Column('character_id', Integer, ForeignKey('characters.id'), nullable=False, unique=True),
            Column('faction', String(32), nullable=False),
            Column('reputation', Integer, nullable=False, server_default='0'),
            Column('claimed_tiers_json', Text, nullable=True),
            Column('unlocked_titles_json', Text, nullable=True),
            Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=True),
        )


def downgrade():
    pass
