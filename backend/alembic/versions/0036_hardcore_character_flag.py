"""hardcore character flag

Revision ID: 0036
Revises: 0035
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '0036'
down_revision = '0035'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    cols = [c['name'] for c in inspector.get_columns('characters')]
    if 'is_hardcore' not in cols:
        op.add_column('characters', sa.Column('is_hardcore', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('characters', 'is_hardcore')
