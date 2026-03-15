"""quest_slots table

Revision ID: 0035
Revises: 0034
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '0035'
down_revision = '0034'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = Inspector.from_engine(bind)
    if 'quest_slots' not in insp.get_table_names():
        op.create_table(
            'quest_slots',
            sa.Column('id',           sa.Integer, primary_key=True),
            sa.Column('character_id', sa.Integer, sa.ForeignKey('characters.id'), nullable=False),
            sa.Column('slot_index',   sa.Integer, nullable=False),
            sa.Column('quest_def_id', sa.Integer, nullable=False),
            sa.Column('skip_count',   sa.Integer, nullable=False, default=0, server_default='0'),
            sa.Column('last_skip_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.func.now()),
            sa.UniqueConstraint('character_id', 'slot_index', name='uq_quest_slots_char_slot'),
        )


def downgrade():
    op.drop_table('quest_slots')
