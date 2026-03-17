"""
routers/prestige.py — Prestige systém (post-level-cap reset)
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from core.logging import get_logger
from models.user import User
from models.character import Character, CLASS_BASE_STATS, CharacterClass
from models.prestige import (
    PrestigeLog, MAX_LEVEL, PRESTIGE_POWER_CAP,
    PRESTIGE_CRYSTAL_REWARD, PRESTIGE_TITLES,
    prestige_title, prestige_bonus_mult, prestige_frame_key,
    PRESTIGE_CLASS_BASE_STATS,
    PRESTIGE_BONUS_ATK_PER_LVL, PRESTIGE_BONUS_DEF_PER_LVL,
    PRESTIGE_BONUS_HP_PER_LVL, PRESTIGE_BONUS_MP_PER_LVL,
)
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

log = get_logger(__name__)
router = APIRouter(prefix="/prestige", tags=["prestige"])


async def _get_char(user: User, db: AsyncSession) -> Character:
    res = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


@router.get("/info")
async def prestige_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí prestige info hráče — aktuální level, bonusy, co se resetuje, podmínky."""
    char = await _get_char(current_user, db)
    pl = char.prestige_level or 0
    next_pl = pl + 1
    mults = prestige_bonus_mult(pl)
    next_mults = prestige_bonus_mult(next_pl)

    # Prestige log
    log_res = await db.execute(
        select(PrestigeLog)
        .where(PrestigeLog.character_id == char.id)
        .order_by(PrestigeLog.prestiged_at.desc())
        .limit(10)
    )
    history = log_res.scalars().all()

    # Nadcházející titul + frame
    upcoming_title = prestige_title(next_pl)
    upcoming_frame = prestige_frame_key(next_pl)

    is_power_capped = pl >= PRESTIGE_POWER_CAP
    can_prestige = char.level >= MAX_LEVEL

    # Pro post-cap: next bonusy jsou stejné jako current (žádný power nárůst)
    display_next_mults = next_mults if not is_power_capped else mults

    return {
        "prestige_level":   pl,
        "max_level":        MAX_LEVEL,
        "power_cap":        PRESTIGE_POWER_CAP,
        "is_power_capped":  is_power_capped,
        "can_prestige":     can_prestige,
        "level":            char.level,
        "current_bonuses": {
            "atk_pct": round((mults["atk"] - 1) * 100, 1),
            "def_pct": round((mults["def"] - 1) * 100, 1),
            "hp_pct":  round((mults["hp"]  - 1) * 100, 1),
            "mp_pct":  round((mults["mp"]  - 1) * 100, 1),
        },
        "next_bonuses": {
            "atk_pct": round((display_next_mults["atk"] - 1) * 100, 1),
            "def_pct": round((display_next_mults["def"] - 1) * 100, 1),
            "hp_pct":  round((display_next_mults["hp"]  - 1) * 100, 1),
            "mp_pct":  round((display_next_mults["mp"]  - 1) * 100, 1),
        },
        "per_level_bonus": {
            "atk_pct":  round(PRESTIGE_BONUS_ATK_PER_LVL * 100, 0),
            "def_pct":  round(PRESTIGE_BONUS_DEF_PER_LVL * 100, 0),
            "hp_pct":   round(PRESTIGE_BONUS_HP_PER_LVL  * 100, 0),
            "mp_pct":   round(PRESTIGE_BONUS_MP_PER_LVL  * 100, 0),
        },
        "crystal_reward":  PRESTIGE_CRYSTAL_REWARD,
        "upcoming_title":  upcoming_title,
        "upcoming_frame":  upcoming_frame,
        "prestige_portrait_frame": char.prestige_portrait_frame,
        "resets": ["level → 1", "XP → 0", "Stat body → 0", "Primary stats → základ třídy", "Talenty → znovu odemčeny při levelování"],
        "keeps":  ["Gold", "Inventář & equipment", "Guild", "Frakce", "Specializace (subclass)", "Arena rank", "Crystaly + odměna"],
        "history": [
            {
                "prestige_level": h.prestige_level,
                "at": h.prestiged_at.isoformat(),
                "crystals": h.reward_crystals,
                "title": h.awarded_title,
                "frame": prestige_frame_key(h.prestige_level),
            }
            for h in history
        ],
        "titles": PRESTIGE_TITLES,
    }


@router.post("/ascend")
async def prestige_ascend(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Provede prestige — reset level na 1, +1 prestige level, trvalé bonusy + crystaly."""
    char = await _get_char(current_user, db)

    if char.level < MAX_LEVEL:
        raise HTTPException(400, f"Prestige vyžaduje dosažení levelu {MAX_LEVEL}. Aktuálně: {char.level}.")

    old_pl = char.prestige_level or 0
    new_pl = old_pl + 1
    is_post_cap = new_pl > PRESTIGE_POWER_CAP

    # ── Reset stats ───────────────────────────────────────────────────────────
    char.level      = 1
    char.xp         = 0
    char.stat_points = 0
    char.talents_json = None  # talenty se znovu odemknou při levelování

    # Reset primary stats na base hodnoty třídy
    base = PRESTIGE_CLASS_BASE_STATS.get(char.cls, {})
    char.strength     = base.get("strength",     5)
    char.dexterity    = base.get("dexterity",    5)
    char.intelligence = base.get("intelligence", 5)
    char.endurance    = base.get("endurance",    5)
    char.luck         = base.get("luck",         5)

    char.prestige_level = new_pl

    # Přepočítej stats (nyní s novým prestige_level mult)
    char.recalculate_stats()

    # ── Portrait frame ────────────────────────────────────────────────────────
    new_frame = prestige_frame_key(new_pl)
    if new_frame:
        char.prestige_portrait_frame = new_frame

    # ── Titul ─────────────────────────────────────────────────────────────────
    new_title = prestige_title(new_pl)
    if new_title and not char.current_title:
        char.current_title = new_title

    # ── Crystaly ──────────────────────────────────────────────────────────────
    char.crystals = (char.crystals or 0) + PRESTIGE_CRYSTAL_REWARD
    from routers.crystals import add_crystals
    # Uložíme log crystalové transakce (bez commit — bude součástí níže)
    await add_crystals(char.id, PRESTIGE_CRYSTAL_REWARD, f"prestige:{new_pl}", db)

    # ── Prestige log ─────────────────────────────────────────────────────────
    entry = PrestigeLog(
        character_id=char.id,
        prestige_level=new_pl,
        prestiged_at=datetime.now(timezone.utc).replace(tzinfo=None),
        reward_crystals=PRESTIGE_CRYSTAL_REWARD,
        awarded_title=new_title,
    )
    db.add(entry)

    await db.commit()
    await db.refresh(char)

    log.info("Prestige ascended", extra={"data": {
        "char": char.name, "prestige_level": new_pl,
        "crystals": PRESTIGE_CRYSTAL_REWARD, "post_cap": is_post_cap,
    }})

    if is_post_cap:
        msg = f"🌟 Prestige {new_pl} dosaženo! Jsi za hranicí moci — tato cesta je čistě legendy."
    else:
        msg = f"🌟 Prestige {new_pl} dosaženo! Tvá síla se přenesla do nové éry."

    return {
        "message":        msg,
        "prestige_level": new_pl,
        "awarded_title":  new_title,
        "awarded_frame":  new_frame,
        "reward_crystals": PRESTIGE_CRYSTAL_REWARD,
        "is_post_cap":    is_post_cap,
        "character":      await char_dict_with_equipment(char, db),
    }
