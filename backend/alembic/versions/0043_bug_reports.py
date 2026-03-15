"""bug_reports table

Revision ID: 0043
Revises: 0042
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = '0043'
down_revision = '0042'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'bug_reports' not in existing_tables:
        op.create_table(
            'bug_reports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(120), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('steps', sa.Text(), nullable=True),
            sa.Column('severity', sa.String(20), nullable=False, server_default='minor'),
            sa.Column('page_context', sa.String(80), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='open'),
            sa.Column('char_name', sa.String(80), nullable=True),
            sa.Column('char_level', sa.Integer(), nullable=True),
            sa.Column('char_class', sa.String(60), nullable=True),
            sa.Column('admin_note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade():
    op.drop_table('bug_reports')
