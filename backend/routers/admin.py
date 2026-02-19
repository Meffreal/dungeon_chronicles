"""
routers/admin.py — Jednoduchy admin panel (statistiky hry)
Chraneno statickym klicem v hlavicce X-Admin-Key.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.user import User
from models.character import Character
from models.quest import Quest
from models.arena import ArenaMatch, Season
from models.guild import Guild
from models.market import MarketListing
from models.achievement import PlayerAchievement

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_KEY = os.getenv("ADMIN_KEY", "dungeon-admin-2024")


def _check_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, "Neplatny admin klic.")


@router.get("/stats", dependencies=[Depends(_check_key)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """Vraci celkove statistiky hry."""
    users_count = (await db.execute(
        select(func.count()).select_from(User)
    )).scalar_one()

    chars_count = (await db.execute(
        select(func.count()).select_from(Character)
    )).scalar_one()

    guilds_count = (await db.execute(
        select(func.count()).select_from(Guild)
    )).scalar_one()

    active_quests = (await db.execute(
        select(func.count()).select_from(ActiveQuest)
    )).scalar_one()

    total_matches = (await db.execute(
        select(func.count()).select_from(ArenaMatch)
    )).scalar_one()

    active_listings = (await db.execute(
        select(func.count())
        .select_from(MarketListing)
        .where(MarketListing.is_sold == False)
    )).scalar_one()

    achievements_awarded = (await db.execute(
        select(func.count()).select_from(PlayerAchievement)
    )).scalar_one()

    # Top 5 hracu podle levelu
    top_chars_res = await db.execute(
        select(Character).order_by(Character.level.desc(), Character.xp.desc()).limit(5)
    )
    top_chars = top_chars_res.scalars().all()
    CLS_E = {"warrior": "Valecnik", "mage": "Mag", "ranger": "Lovec"}

    # Aktivni sezona
    season_res = await db.execute(
        select(Season).where(Season.is_active == True).order_by(Season.id.desc())
    )
    season = season_res.scalar_one_or_none()

    return {
        "overview": {
            "users":               users_count,
            "characters":          chars_count,
            "guilds":              guilds_count,
            "active_quests":       active_quests,
            "arena_matches_total": total_matches,
            "market_listings":     active_listings,
            "achievements_given":  achievements_awarded,
        },
        "top_characters": [
            {
                "name":  c.name,
                "cls":   CLS_E.get(c.cls, c.cls),
                "level": c.level,
                "gold":  c.gold,
                "elo":   c.arena_rank,
            }
            for c in top_chars
        ],
        "current_season": season.to_dict() if season else None,
    }


@router.get("/users", dependencies=[Depends(_check_key)])
async def admin_users(db: AsyncSession = Depends(get_db)):
    """Seznam vsech uzivatelu + jejich postava."""
    users_res = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = users_res.scalars().all()

    out = []
    for u in users:
        char_res = await db.execute(
            select(Character).where(Character.user_id == u.id)
        )
        char = char_res.scalar_one_or_none()
        out.append({
            "id":         u.id,
            "username":   u.username,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "character":  {
                "name":  char.name,
                "cls":   char.cls,
                "level": char.level,
                "gold":  char.gold,
            } if char else None,
        })

    return {"users": out, "total": len(out)}
