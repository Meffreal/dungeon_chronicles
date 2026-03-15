"""
routers/dungeon_modifier.py — Týdenní dungeon modifier endpointy.

GET /dungeon/modifier   — aktuální týdenní modifikátor (bez auth)
GET /dungeon/modifiers  — všechny definované modifikátory (bez auth)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
from typing import Optional

from database import get_db, AsyncSessionLocal
from models.dungeon_modifier import WeeklyDungeonModifier, _week_modifier_key, _current_week_start

router = APIRouter(prefix="/dungeon", tags=["dungeon-modifier"])


async def ensure_active_modifier(db: Optional[AsyncSession] = None) -> WeeklyDungeonModifier:
    """
    Zajistí, že existuje aktivní modifikátor pro aktuální týden.
    - Pokud existuje a je aktuální → vrátí ho.
    - Pokud je zastaralý → deaktivuje ho, vytvoří nový pro tento týden.
    - Volatelné bez DB session (vytvoří si vlastní) pro lifespan init.
    """
    own_db = db is None
    if own_db:
        db = AsyncSessionLocal()

    try:
        week_start = _current_week_start()
        week_end   = week_start + timedelta(days=7)

        # Hledej aktivní modifikátor
        result = await db.execute(
            select(WeeklyDungeonModifier)
            .where(WeeklyDungeonModifier.is_active == True)  # noqa: E712
            .order_by(WeeklyDungeonModifier.id.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()

        # Pokud existuje aktivní a patří k tomuto týdnu → OK
        if existing and existing.week_start >= week_start:
            return existing

        # Deaktivuj starý
        if existing:
            existing.is_active = False

        # Vytvoř nový pro tento týden
        key = _week_modifier_key(week_start)
        new_mod = WeeklyDungeonModifier(
            modifier_key=key,
            week_start=week_start,
            week_end=week_end,
            is_active=True,
        )
        db.add(new_mod)
        await db.commit()
        await db.refresh(new_mod)
        return new_mod
    finally:
        if own_db:
            await db.close()


@router.get("/modifier")
async def get_current_modifier(db: AsyncSession = Depends(get_db)):
    """Vrátí aktuální týdenní modifikátor dungeonů včetně zbývajícího času."""
    mod = await ensure_active_modifier(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seconds_remaining = max(0, int((mod.week_end - now).total_seconds()))

    result = mod.to_dict()
    result["seconds_remaining"] = seconds_remaining
    return result


@router.get("/modifiers")
async def list_all_modifiers():
    """Vrátí všechny definované modifikátory (statická data pro info panel)."""
    from game.dungeon_modifiers import DUNGEON_MODIFIERS
    return {
        "modifiers": [
            {"key": k, **{fk: fv for fk, fv in v.items()}}
            for k, v in DUNGEON_MODIFIERS.items()
        ]
    }
