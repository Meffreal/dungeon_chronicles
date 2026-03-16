"""
routers/season_pass.py — Sezónní progression (free track)

Endpointy:
- GET  /season-pass/              — aktuální sezóna + progress hráče
- POST /season-pass/claim/{tier}  — vyzvednutí odměny za dosažený tier
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character
from models.economy import log_gold, GoldReason
from models.season_pass import (
    SeasonPass, SeasonPassProgress,
    SEASON_TIERS, SEASON_XP_SOURCES, get_reached_tier,
)
from game.season_pass_manager import ensure_active_season_pass
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/season-pass", tags=["season-pass"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _get_or_create_progress(
    character_id: int,
    season_id: int,
    db: AsyncSession,
) -> SeasonPassProgress:
    res = await db.execute(
        select(SeasonPassProgress).where(
            SeasonPassProgress.character_id == character_id,
            SeasonPassProgress.season_id    == season_id,
        )
    )
    prog = res.scalar_one_or_none()
    if prog is None:
        prog = SeasonPassProgress(
            character_id=character_id,
            season_id=season_id,
            season_xp=0,
            claimed_tiers="[]",
        )
        db.add(prog)
        await db.flush()
    return prog


async def add_season_xp(
    character_id: int,
    source: str,
    db: AsyncSession,
) -> None:
    """
    Přidá season XP hráči za danou aktivitu.
    source je klíč z SEASON_XP_SOURCES.
    Voláno z quest.py, arena.py, dungeon.py, weekly_quest.py.
    """
    amount = SEASON_XP_SOURCES.get(source, 0)
    if amount <= 0:
        return

    season = await ensure_active_season_pass(db)
    prog   = await _get_or_create_progress(character_id, season.id, db)
    prog.season_xp += amount


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def get_season_pass(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí aktuální sezónu a progress hráče."""
    char   = await _get_char(user, db)
    season = await ensure_active_season_pass(db)
    prog   = await _get_or_create_progress(char.id, season.id, db)
    await db.commit()

    return {
        "season":   season.to_dict(),
        "progress": prog.to_dict(),
        "xp_sources": SEASON_XP_SOURCES,
    }


@router.post("/claim/{tier}")
async def claim_tier(
    tier: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyzvedne odměnu za dosažený tier. Tier musí být dosažen a ještě nevyzvednutý."""
    char   = await _get_char(user, db)
    season = await ensure_active_season_pass(db)
    prog   = await _get_or_create_progress(char.id, season.id, db)

    tier_def = next((t for t in SEASON_TIERS if t["tier"] == tier), None)
    if not tier_def:
        raise HTTPException(404, f"Tier {tier} neexistuje.")

    if prog.season_xp < tier_def["xp_req"]:
        raise HTTPException(400, f"Ještě nemáš dost Season XP. Potřebuješ {tier_def['xp_req']}, máš {prog.season_xp}.")

    claimed = prog.get_claimed()
    if tier in claimed:
        raise HTTPException(400, "Tato odměna již byla vyzvednutá.")

    prog.mark_claimed(tier)

    reward_type     = tier_def["reward_type"]
    reward_title    = tier_def.get("reward_title")
    reward_gold     = tier_def.get("reward_gold", 0)
    reward_crystals = tier_def.get("reward_crystals", 0)

    # Aplikuj odměny
    if reward_type in ("title", "title_and_gold") and reward_title:
        char.current_title = reward_title

    if reward_type in ("gold", "title_and_gold") and reward_gold:
        char.gold += reward_gold
        await log_gold(
            db, char, reward_gold, GoldReason.QUEST_REWARD,
            {"source": "season_pass", "tier": tier},
        )

    if reward_crystals > 0:
        from routers.crystals import add_crystals
        await add_crystals(char.id, reward_crystals, f"season_tier:{tier}", db)

    await db.commit()
    await db.refresh(char)

    msg_parts = []
    if reward_title:
        msg_parts.append(f'Titul "{reward_title}"')
    if reward_gold:
        msg_parts.append(f"+{reward_gold:,} G".replace(",", " "))
    if reward_crystals:
        msg_parts.append(f"+{reward_crystals} 💎")

    return {
        "message":         f"Tier {tier} odměna vyzvednutá: {' · '.join(msg_parts)}!",
        "reward_type":     reward_type,
        "reward_title":    reward_title,
        "reward_gold":     reward_gold,
        "reward_crystals": reward_crystals,
        "season_xp":       prog.season_xp,
        "character":       await char_dict_with_equipment(char, db),
    }
