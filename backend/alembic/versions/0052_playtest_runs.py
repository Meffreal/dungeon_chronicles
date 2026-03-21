"""Add playtest_runs table

Revision ID: 0052
Revises: 0051
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0052'
down_revision = '0051'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    existing = insp.get_table_names()
    if 'playtest_runs' in existing:
        return  # idempotent guard

    op.create_table(
        'playtest_runs',
        sa.Column('id',              sa.Integer(),   primary_key=True),
        sa.Column('char_id',         sa.Integer(),   sa.ForeignKey('characters.id'), nullable=False, index=True),
        sa.Column('dungeon_key',     sa.String(32),  nullable=False),
        sa.Column('status',          sa.String(16),  nullable=False, server_default='active'),
        sa.Column('map_data',        sa.Text(),      nullable=True),
        sa.Column('current_node_id', sa.String(32),  nullable=True),
        sa.Column('visited_nodes',   sa.Text(),      nullable=True),
        sa.Column('relics',          sa.Text(),      nullable=True),
        sa.Column('pending_relics',  sa.Text(),      nullable=True),
        sa.Column('hp_current',      sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('hp_max',          sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('run_gold',        sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('reward_xp',       sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('reward_gold',     sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('reward_claimed',  sa.Boolean(),   nullable=False, server_default='0'),
        sa.Column('cooldown_until',  sa.DateTime(),  nullable=True),
        sa.Column('created_at',      sa.DateTime(),  nullable=False),
    )


def downgrade():
    op.drop_table('playtest_runs')
