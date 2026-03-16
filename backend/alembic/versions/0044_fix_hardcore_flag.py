"""fix hardcore flag — reset is_hardcore and revive bugged dead characters

Revision ID: 0044
Revises: 0043
Create Date: 2026-03-16
"""
from alembic import op
from sqlalchemy import inspect as sa_inspect

revision = '0044'
down_revision = '0043'
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
            f"0044_fix_hardcore_flag: chybí sloupce v tabulce 'characters': {missing}. "
            "Spusť nejdřív předchozí migrace."
        )

    # 1. Nastavit is_hardcore = FALSE pro všechny postavy
    op.execute("UPDATE characters SET is_hardcore = FALSE")

    # 2. Revivnout všechny mrtvé postavy — čistíme stav způsobený bugem
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

    # Obnoví původní (buggy) stav — is_hardcore = TRUE pro všechny
    # Mrtvé postavy nelze bezpečně obnovit (data jsou nenávratně smazána)
    op.execute("UPDATE characters SET is_hardcore = TRUE")
