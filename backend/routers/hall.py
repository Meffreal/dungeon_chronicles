"""
routers/hall.py — Hall of the Fallen API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.hall_of_fallen import HallOfFallen
from routers.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/hall", tags=["hall"])


@router.get("/fallen")
async def hall_of_fallen(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Veřejný Hall of the Fallen — seznam padlých hrdinů (nejnovější první)."""
    result = await db.execute(
        select(HallOfFallen)
        .order_by(HallOfFallen.died_at.desc())
        .limit(limit)
        .offset(offset)
    )
    entries = result.scalars().all()

    total_res = await db.execute(select(func.count(HallOfFallen.id)))
    total = total_res.scalar_one()

    return {
        "total":   total,
        "entries": [e.to_dict() for e in entries],
    }


@router.get("/fallen/my")
async def my_fallen_heroes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Padlí hrdinové přihlášeného uživatele."""
    result = await db.execute(
        select(HallOfFallen)
        .where(HallOfFallen.user_id == user.id)
        .order_by(HallOfFallen.died_at.desc())
    )
    entries = result.scalars().all()
    return {"entries": [e.to_dict() for e in entries], "count": len(entries)}


@router.get("/ladder")
async def living_ladder(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Living Ladder — žijící postavy seřazené dle levelu (veřejný leaderboard)."""
    from models.character import Character
    result = await db.execute(
        select(Character)
        .where(Character.is_dead == False)
        .order_by(Character.level.desc(), Character.xp.desc())
        .limit(limit)
    )
    chars = result.scalars().all()
    return {
        "entries": [
            {
                "rank":    i + 1,
                "name":    c.name,
                "cls":     c.cls,
                "level":   c.level,
                "faction": getattr(c, 'faction', None),
            }
            for i, c in enumerate(chars)
        ]
    }
