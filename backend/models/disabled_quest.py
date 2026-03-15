"""
models/disabled_quest.py — DB-backed seznam deaktivovaných questů.

Nahrazuje in-memory `_DISABLED_QUESTS: set[int]` v models/quest.py.
Umožňuje admin toggles fungovat napříč všemi instancemi serveru.

Architektura:
  - DB tabulka `disabled_quests` jako autoritativní stav
  - Per-instance in-memory cache s TTL 10 s (omezuje DB dotazy)
  - Cache se invaliduje automaticky po toggleu na dané instanci
"""
import time
from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from database import Base


class DisabledQuest(Base):
    """Quest deaktivovaný adminem."""
    __tablename__ = "disabled_quests"

    quest_id:    Mapped[int]           = mapped_column(Integer, primary_key=True)
    disabled_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)


# ── Per-instance cache ─────────────────────────────────────────────────────────
_cache: set[int] | None = None
_cache_at: float = 0.0
_CACHE_TTL: float = 10.0   # sekund


def _invalidate_cache() -> None:
    """Okamžitě zneplatní cache na této instanci."""
    global _cache, _cache_at
    _cache = None
    _cache_at = 0.0


async def get_disabled_quest_ids(db: AsyncSession) -> set[int]:
    """
    Vrátí set deaktivovaných quest ID.
    Čerpá z per-instance cache (TTL 10 s) nebo DB.
    """
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < _CACHE_TTL:
        return _cache

    result = await db.execute(select(DisabledQuest.quest_id))
    ids = set(result.scalars().all())
    _cache    = ids
    _cache_at = now
    return ids


async def disable_quest(quest_id: int, db: AsyncSession) -> None:
    """Deaktivuje quest v DB a invaliduje cache."""
    result = await db.execute(select(DisabledQuest).where(DisabledQuest.quest_id == quest_id))
    if not result.scalar_one_or_none():
        db.add(DisabledQuest(
            quest_id=quest_id,
            disabled_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
        await db.commit()
    _invalidate_cache()


async def enable_quest(quest_id: int, db: AsyncSession) -> None:
    """Znovu aktivuje quest v DB a invaliduje cache."""
    result = await db.execute(select(DisabledQuest).where(DisabledQuest.quest_id == quest_id))
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    _invalidate_cache()
