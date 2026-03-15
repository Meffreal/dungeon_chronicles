"""baseline — existující schéma zachováno, Alembic začíná sledovat verze

Revision ID: 0001
Revises:
Create Date: 2026-02-27

Poznámka:
  Tato migrace je záměrně prázdná. Databáze byla vytvořena přes
  Base.metadata.create_all() ještě před zavedením Alembic.
  upgrade() je prázdné → žádné DDL změny.
  Nové schéma změny přidávej jako 0002, 0003, ...
"""
from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline — databáze již existuje, nic neměníme
    pass


def downgrade() -> None:
    # Baseline nelze "odmigrovat" — je to výchozí stav
    pass
