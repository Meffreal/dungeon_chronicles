"""hall of the fallen table

Revision ID: 0041
Revises: 0040
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0041'
down_revision = '0040'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'hall_of_fallen' not in inspector.get_table_names():
        op.create_table(
            'hall_of_fallen',
            sa.Column('id',               sa.Integer(),   nullable=False),
            sa.Column('user_id',          sa.Integer(),   nullable=False),
            sa.Column('character_id',     sa.Integer(),   nullable=False),
            sa.Column('hero_name',        sa.String(64),  nullable=False),
            sa.Column('hero_cls',         sa.String(32),  nullable=False),
            sa.Column('hero_level',       sa.Integer(),   nullable=False),
            sa.Column('hero_faction',     sa.String(64),  nullable=True),
            sa.Column('killed_by',        sa.String(255), nullable=True),
            sa.Column('death_dungeon',    sa.String(255), nullable=True),
            sa.Column('died_at',          sa.DateTime(),  nullable=False),
            sa.Column('days_survived',    sa.Integer(),   nullable=False, server_default='0'),
            sa.Column('dungeons_cleared', sa.Integer(),   nullable=False, server_default='0'),
            sa.Column('build_snapshot',   sa.JSON(),      nullable=True),
            sa.Column('epitaph',          sa.String(280), nullable=True),
            sa.Column('recorded_at',      sa.DateTime(),  nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade():
    op.drop_table('hall_of_fallen')
