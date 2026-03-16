"""
routers/bloodline.py — Bloodline meta-progression API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character
from routers.auth import get_current_user
from game.bloodline import (
    get_or_create_bloodline,
    bloodline_xp_progress,
    get_unlocks_for_level,
    generate_ancestor_memories,
)

router = APIRouter(prefix="/bloodline", tags=["bloodline"])


@router.get("/status")
async def bloodline_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí aktuální stav Bloodline: level, XP, odemčené bonusy, padlí hrdinové."""
    bloodline = await get_or_create_bloodline(user.id, db)
    progress = bloodline_xp_progress(bloodline.total_xp)
    unlocks = get_unlocks_for_level(bloodline.level)

    # Načti padlé hrdiny tohoto uživatele (is_dead=True)
    fallen_result = await db.execute(
        select(Character).where(
            Character.user_id == user.id,
            Character.is_dead == True,
        ).order_by(Character.died_at.desc())
    )
    fallen_chars = fallen_result.scalars().all()

    fallen_heroes = [
        {
            "name":           c.name,
            "cls":            c.cls,
            "level":          c.level,
            "killed_by":      c.killed_by,
            "death_dungeon":  c.death_dungeon,
            "days_survived":  (
                (c.died_at - (c.created_at.replace(tzinfo=None) if getattr(c.created_at, 'tzinfo', None) else c.created_at)).days
                if c.died_at and c.created_at else 0
            ),
        }
        for c in fallen_chars
    ]

    # Ancestor Memories (level 21+)
    ancestor_memories = []
    if bloodline.level >= 21:
        ancestor_memories = generate_ancestor_memories(fallen_heroes)

    return {
        "level":             bloodline.level,
        "total_xp":          bloodline.total_xp,
        "xp_in_level":       progress["xp_in_level"],
        "xp_needed":         progress["xp_needed"],
        "is_max_level":      progress["is_max_level"],
        "unlocks":           unlocks,
        "fallen_heroes":     fallen_heroes,
        "fallen_count":      len(fallen_heroes),
        "ancestor_memories": ancestor_memories,
    }
