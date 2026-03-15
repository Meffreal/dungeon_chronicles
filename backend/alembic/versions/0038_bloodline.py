"""bloodline meta-progression table

Revision ID: 0038
Revises: 0037
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '0038'
down_revision = '0037'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()
    if 'bloodlines' not in tables:
        op.create_table(
            'bloodlines',
            sa.Column('id',           sa.Integer(),  nullable=False),
            sa.Column('user_id',      sa.Integer(),  nullable=False),
            sa.Column('total_xp',     sa.Integer(),  nullable=False, server_default='0'),
            sa.Column('level',        sa.Integer(),  nullable=False, server_default='0'),
            sa.Column('unlocks_json', sa.JSON(),     nullable=True),
            sa.Column('created_at',   sa.DateTime(), nullable=True),
            sa.Column('updated_at',   sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id'),
        )


def downgrade():
    op.drop_table('bloodlines')
