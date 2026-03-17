"""0048_stat_system_redesign — odstraní staré combat staty z characters a items, přidá bonus_xp"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0048'
down_revision = '0047'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # -- characters: odstraň atk, def_, spd, mp_max
    char_cols = [c['name'] for c in insp.get_columns('characters')]
    for col in ('atk', 'def_', 'spd', 'mp_max'):
        if col in char_cols:
            op.drop_column('characters', col)

    # -- items: odstraň bonus_spd, bonus_mp; přidej bonus_xp
    item_cols = [c['name'] for c in insp.get_columns('items')]
    for col in ('bonus_spd', 'bonus_mp'):
        if col in item_cols:
            op.drop_column('items', col)
    if 'bonus_xp' not in item_cols:
        op.add_column('items', sa.Column('bonus_xp', sa.Integer(),
                                         nullable=False, server_default='0'))

def downgrade():
    # Opačné operace pro rollback
    op.add_column('characters', sa.Column('atk',    sa.Integer(), server_default='10'))
    op.add_column('characters', sa.Column('def_',   sa.Integer(), server_default='5'))
    op.add_column('characters', sa.Column('spd',    sa.Integer(), server_default='8'))
    op.add_column('characters', sa.Column('mp_max', sa.Integer(), server_default='50'))
    op.add_column('items', sa.Column('bonus_spd', sa.Integer(), server_default='0'))
    op.add_column('items', sa.Column('bonus_mp',  sa.Integer(), server_default='0'))
    op.drop_column('items', 'bonus_xp')
