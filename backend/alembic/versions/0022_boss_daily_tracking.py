"""0022 — Boss daily tracking

Revision ID: 0022
Revises: 0021
Create Date: 2026-03-06

Přidá na boss_participations:
  daily_damage  INT DEFAULT 0   — poškození způsobené dnešní UTC den
  daily_date    DATE            — datum kdy byl daily_damage naposledy aktualizován
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision    = '0022'
down_revision = '0021'
branch_labels = None
depends_on    = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    cols = [c['name'] for c in insp.get_columns('boss_participations')]

    if 'daily_damage' not in cols:
        op.add_column(
            'boss_participations',
            sa.Column('daily_damage', sa.Integer(), nullable=False, server_default='0'),
        )
    if 'daily_date' not in cols:
        op.add_column(
            'boss_participations',
            sa.Column('daily_date', sa.Date(), nullable=True),
        )


def downgrade():
    op.drop_column('boss_participations', 'daily_date')
    op.drop_column('boss_participations', 'daily_damage')
