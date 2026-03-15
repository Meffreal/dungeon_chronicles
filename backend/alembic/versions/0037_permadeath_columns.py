"""permadeath columns

Revision ID: 0037
Revises: 0036
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '0037'
down_revision = '0036'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    cols = [c['name'] for c in inspector.get_columns('characters')]
    if 'is_dead' not in cols:
        op.add_column('characters', sa.Column('is_dead', sa.Boolean(), nullable=False, server_default='0'))
    if 'died_at' not in cols:
        op.add_column('characters', sa.Column('died_at', sa.DateTime(), nullable=True))
    if 'killed_by' not in cols:
        op.add_column('characters', sa.Column('killed_by', sa.String(255), nullable=True))
    if 'death_dungeon' not in cols:
        op.add_column('characters', sa.Column('death_dungeon', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('characters', 'death_dungeon')
    op.drop_column('characters', 'killed_by')
    op.drop_column('characters', 'died_at')
    op.drop_column('characters', 'is_dead')
