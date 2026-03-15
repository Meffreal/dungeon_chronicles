"""0027 — Profession konsolidace (6 → 3)

Revision ID: 0027
Revises: 0026
Create Date: 2026-03-06

Sloučí staré profession_key hodnoty na nové konsolidované:
  runosmith + soulforger → runist
  diviner   + fateweaver → oracle
  gambler   + agent      → broker

Pokud má postava dvě profese mapující na stejný nový klíč,
zachová se lepší (vyšší rank; při shodě preferujeme aktivní slot).
Duplicitní řádek se smaže.
"""
from collections import defaultdict
import sqlalchemy as sa
from alembic import op

revision      = '0027'
down_revision = '0026'
branch_labels = None
depends_on    = None

MIGRATION_MAP = {
    "runosmith":  "runist",
    "soulforger": "runist",
    "diviner":    "oracle",
    "fateweaver": "oracle",
    "gambler":    "broker",
    "agent":      "broker",
}


def upgrade() -> None:
    bind = op.get_bind()

    # Načti všechny řádky se starými klíči
    result = bind.execute(sa.text(
        "SELECT id, character_id, profession_key, rank, xp, is_active, slot "
        "FROM character_professions "
        "WHERE profession_key IN ('runosmith','soulforger','diviner','fateweaver','gambler','agent')"
    ))
    rows = result.fetchall()

    # Seskup podle (character_id, nový klíč)
    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        new_key = MIGRATION_MAP.get(row[2], row[2])   # row[2] = profession_key
        groups[(row[1], new_key)].append(row)          # row[1] = character_id

    for (char_id, new_key), group_rows in groups.items():
        if len(group_rows) == 1:
            # Jen přejmenuj klíč
            bind.execute(sa.text(
                "UPDATE character_professions SET profession_key = :nk WHERE id = :rid"
            ), {"nk": new_key, "rid": group_rows[0][0]})
        else:
            # Dvě profese → zachovat lepší: vyšší rank, při shodě preferuj aktivní
            # row: (id, character_id, profession_key, rank, xp, is_active, slot)
            group_rows_sorted = sorted(
                group_rows,
                key=lambda r: (r[3], 1 if r[5] else 0),  # rank DESC, is_active DESC
                reverse=True,
            )
            keep = group_rows_sorted[0]
            to_delete = [r[0] for r in group_rows_sorted[1:]]

            # Pokud není aktivní keeper, ale mazaný ano — přenést slot info
            if not keep[5] and any(r[5] for r in group_rows_sorted[1:]):
                active_one = next(r for r in group_rows_sorted[1:] if r[5])
                bind.execute(sa.text(
                    "UPDATE character_professions "
                    "SET profession_key = :nk, is_active = 1, slot = :sl, "
                    "    activated_at = :at "
                    "WHERE id = :rid"
                ), {"nk": new_key, "sl": active_one[6], "at": None, "rid": keep[0]})
            else:
                bind.execute(sa.text(
                    "UPDATE character_professions SET profession_key = :nk WHERE id = :rid"
                ), {"nk": new_key, "rid": keep[0]})

            for del_id in to_delete:
                bind.execute(sa.text(
                    "DELETE FROM character_professions WHERE id = :rid"
                ), {"rid": del_id})


def downgrade() -> None:
    # Downgrade není plně reverzibilní — nejde obnovit původní mapování
    # bez zálohy dat. Doporučuje se záloha DB před upgrade.
    pass
