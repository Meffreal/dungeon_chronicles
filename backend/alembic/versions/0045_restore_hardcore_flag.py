"""restore hardcore flag — hra je HC by design, oprava chyby migrace 0044

Migrace 0044 omylem nastavila is_hardcore=FALSE pro všechny postavy.
Hra je celá navržena jako hardcore — permadeath je výchozí chování.
Tato migrace obnoví is_hardcore=TRUE a vyčistí zbývající is_dead z původního bugu.

Revision ID: 0045
Revises: 0044
Create Date: 2026-03-16
"""
from alembic import op
from sqlalchemy import inspect as sa_inspect

revision = '0045'
down_revision = '0044'
branch_labels = None
depends_on = None

REQUIRED_COLS = {'is_hardcore', 'is_dead', 'killed_by', 'death_dungeon', 'died_at'}


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('characters')}

    missing = REQUIRED_COLS - existing_cols
    if missing:
        raise RuntimeError(
            f"0045_restore_hardcore_flag: chybí sloupce v tabulce 'characters': {missing}. "
            "Spusť nejdřív předchozí migrace."
        )

    # 1. Obnovit is_hardcore = TRUE pro všechny živé postavy
    #    (mrtvé z bugu jsou níže oživeny, pak také dostanou TRUE)
    op.execute("UPDATE characters SET is_hardcore = TRUE")

    # 2. Vyčistit zbývající is_dead flags z původního bugu (is_hardcore byl False,
    #    takže šlo o bugged stav, ne legitimní HC smrt)
    op.execute(
        "UPDATE characters "
        "SET is_dead = FALSE, killed_by = NULL, death_dungeon = NULL, died_at = NULL "
        "WHERE is_dead = TRUE"
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('characters')}

    if 'is_hardcore' not in existing_cols:
        return

    # Vrátí stav po migraci 0044 (všechny non-HC, živé)
    op.execute("UPDATE characters SET is_hardcore = FALSE")
