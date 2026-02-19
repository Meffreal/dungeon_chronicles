"""
routers/achievements.py — Achievementy hráče
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character
from models.achievement import PlayerAchievement, ACHIEVEMENT_DEFINITIONS, ACHIEVEMENT_CATEGORY_NAMES
from routers.auth import get_current_user

router = APIRouter(prefix="/achievements", tags=["achievements"])


async def _get_char(user: User, db: AsyncSession) -> Character:
    from fastapi import HTTPException
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


@router.get("/")
async def get_achievements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí všechny achievementy s info o odemčení pro aktuálního hráče."""
    char = await _get_char(user, db)

    # Načti odemčené
    res = await db.execute(
        select(PlayerAchievement)
        .where(PlayerAchievement.character_id == char.id)
    )
    unlocked = {pa.achievement_id: pa for pa in res.scalars().all()}

    total_points = sum(
        defn[5] for defn in ACHIEVEMENT_DEFINITIONS
        if defn[0] in unlocked
    )

    # Sestav seznam
    categories: dict[str, list] = {}
    for defn in ACHIEVEMENT_DEFINITIONS:
        ach_id, name, desc, icon, category, points, ctype, cvalue = defn
        pa = unlocked.get(ach_id)
        entry = {
            "id":          ach_id,
            "name":        name,
            "desc":        desc,
            "icon":        icon,
            "category":    category,
            "category_name": ACHIEVEMENT_CATEGORY_NAMES.get(category, category),
            "points":      points,
            "unlocked":    pa is not None,
            "unlocked_at": pa.unlocked_at.isoformat() if pa else None,
        }
        categories.setdefault(category, []).append(entry)

    return {
        "total_points":    total_points,
        "max_points":      sum(d[5] for d in ACHIEVEMENT_DEFINITIONS),
        "unlocked_count":  len(unlocked),
        "total_count":     len(ACHIEVEMENT_DEFINITIONS),
        "categories":      categories,
        "category_names":  ACHIEVEMENT_CATEGORY_NAMES,
    }
