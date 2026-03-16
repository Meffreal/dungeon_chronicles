"""
routers/achievements.py — Achievementy hráče
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character
from models.achievement import (
    PlayerAchievement, ACHIEVEMENT_DEFINITIONS, ACHIEVEMENT_CATEGORY_NAMES,
    PlayerChainCompletion, CHAIN_DEFINITIONS,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/achievements", tags=["achievements"])


async def _get_char(user: User, db: AsyncSession) -> Character:
    from fastapi import HTTPException
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
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
        ach_id, name, desc, icon, category, points, title, ctype, cvalue = defn
        pa = unlocked.get(ach_id)
        entry = {
            "id":          ach_id,
            "name":        name,
            "desc":        desc,
            "icon":        icon,
            "category":    category,
            "category_name": ACHIEVEMENT_CATEGORY_NAMES.get(category, category),
            "points":      points,
            "title":       title,
            "unlocked":    pa is not None,
            "unlocked_at": pa.unlocked_at.isoformat() if pa else None,
        }
        categories.setdefault(category, []).append(entry)

    # ── Chain data ────────────────────────────────────────────────────────
    chain_res = await db.execute(
        select(PlayerChainCompletion)
        .where(PlayerChainCompletion.character_id == char.id)
    )
    completed_chains = {cc.chain_id: cc for cc in chain_res.scalars().all()}

    # Mapa achievement ID → info (pro step detail)
    ach_map = {defn[0]: defn for defn in ACHIEVEMENT_DEFINITIONS}

    chains_out = []
    for chain in CHAIN_DEFINITIONS:
        cid = chain["id"]
        cc = completed_chains.get(cid)
        steps_done = sum(1 for sid in chain["steps"] if sid in unlocked)

        steps_detail = []
        for sid in chain["steps"]:
            defn = ach_map.get(sid)
            if defn:
                steps_detail.append({
                    "id":       defn[0],
                    "name":     defn[1],
                    "icon":     defn[3],
                    "unlocked": sid in unlocked,
                })

        chains_out.append({
            "id":              cid,
            "name":            chain["name"],
            "desc":            chain["desc"],
            "icon":            chain["icon"],
            "reward_crystals": chain["reward_crystals"],
            "reward_title":    chain["reward_title"],
            "steps":           steps_detail,
            "steps_done":      steps_done,
            "steps_total":     len(chain["steps"]),
            "completed":       cc is not None,
            "completed_at":    cc.completed_at.isoformat() if cc else None,
        })

    return {
        "total_points":    total_points,
        "max_points":      sum(d[5] for d in ACHIEVEMENT_DEFINITIONS),
        "unlocked_count":  len(unlocked),
        "total_count":     len(ACHIEVEMENT_DEFINITIONS),
        "categories":      categories,
        "category_names":  ACHIEVEMENT_CATEGORY_NAMES,
        "chains":          chains_out,
    }
