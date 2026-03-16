"""multi_char_per_user — drop unique constraint na characters.user_id

Hráč může mít více postav (jedna živá, ostatní mrtvé HC postavy).
Unique constraint na user_id bránil vytvoření nové postavy po permadeath.

Revision ID: 0046
Revises: 0045
Create Date: 2026-03-16
"""
from alembic import op
from sqlalchemy import inspect

revision = '0046'
down_revision = '0045'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Drop unique constraint (PostgreSQL jméno: characters_user_id_key)
    constrs = [c['name'] for c in inspector.get_unique_constraints('characters')]
    if 'characters_user_id_key' in constrs:
        op.drop_constraint('characters_user_id_key', 'characters', type_='unique')

    # Vytvoř non-unique index pro výkon (pokud ještě neexistuje)
    indexes = [i['name'] for i in inspector.get_indexes('characters')]
    if 'ix_characters_user_id' not in indexes:
        op.create_index('ix_characters_user_id', 'characters', ['user_id'])


def downgrade():
    op.drop_index('ix_characters_user_id', 'characters')
    op.create_unique_constraint('characters_user_id_key', 'characters', ['user_id'])
