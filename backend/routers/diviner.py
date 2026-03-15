"""
routers/diviner.py — Věštec: tvorba proroctví, jejich prodej a verifikace
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.economy import log_gold, GoldReason
from models.user import User
from models.character import Character
from models.diviner import (
    ProphecyScroll, PROPHECY_MAX_ACTIVE, PROPHECY_XP, PREDICTION_TYPES,
)
from models.quest import QUEST_DEFINITIONS
from game.professions import get_char, require_active_profession, award_xp
from routers.auth import get_current_user

router = APIRouter(prefix="/diviner", tags=["diviner"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateScrollRequest(BaseModel):
    quest_def_id:     int
    prediction_type:  str    # quest_success | quest_drop_rarity
    prediction_value: str    # success | fail | common | uncommon | rare | epic | legendary
    price:            int    # cena svitku v zlatě


class BuyScrollRequest(BaseModel):
    scroll_id: int


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/scrolls")
async def browse_scrolls(
    db: AsyncSession = Depends(get_db),
):
    """
    Zobrazí dostupné proroctví na Věštecké burze.
    Kupující nevidí konkrétní předpověď — jen o čem svitek je a jeho cenu.
    """
    result = await db.execute(
        select(ProphecyScroll)
        .options(selectinload(ProphecyScroll.creator))
        .where(ProphecyScroll.sold_to_char_id == None)
        .order_by(ProphecyScroll.created_at.desc())
    )
    scrolls = result.scalars().all()
    active = [s for s in scrolls if not s.is_expired]
    return {"scrolls": [s.to_dict(for_buyer=False) for s in active]}


@router.get("/my-scrolls")
async def my_scrolls(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vlastní svitky Věštce — stav, přesnost, XP."""
    char = await get_char(user, db)

    result = await db.execute(
        select(ProphecyScroll)
        .where(ProphecyScroll.creator_char_id == char.id)
        .order_by(ProphecyScroll.created_at.desc())
        .limit(50)
    )
    scrolls = result.scalars().all()

    verified = [s for s in scrolls if s.is_verified]
    correct  = [s for s in verified if s.was_correct]
    accuracy = round(len(correct) / len(verified) * 100, 1) if verified else 0.0

    return {
        "scrolls":        [s.to_dict(for_buyer=True) for s in scrolls],
        "stats": {
            "total":    len(scrolls),
            "verified": len(verified),
            "correct":  len(correct),
            "accuracy": accuracy,
        },
    }


@router.post("/create")
async def create_scroll(
    req:  CreateScrollRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Věštec vytvoří prophecy svitek.
    Max PROPHECY_MAX_ACTIVE aktivních svitků najednou.
    XP: malé za vytvoření, velké za správnou předpověď po verifikaci.
    """
    char = await get_char(user, db)
    await require_active_profession(char.id, "oracle", db)

    # Validace
    if req.prediction_type not in PREDICTION_TYPES:
        raise HTTPException(400, f"Neplatný typ predikce. Možnosti: {PREDICTION_TYPES}")
    if req.price < 1:
        raise HTTPException(400, "Cena musí být alespoň 1 G.")

    # Zkontroluj že quest existuje
    qdef = next((q for q in QUEST_DEFINITIONS if q[0] == req.quest_def_id), None)
    if not qdef:
        raise HTTPException(404, f"Quest #{req.quest_def_id} neexistuje.")

    # Max aktivních svitků
    active_res = await db.execute(
        select(func.count(ProphecyScroll.id)).where(
            ProphecyScroll.creator_char_id == char.id,
            ProphecyScroll.sold_to_char_id == None,
            ProphecyScroll.is_verified == False,
        )
    )
    active_count = active_res.scalar_one()
    if active_count >= PROPHECY_MAX_ACTIVE:
        raise HTTPException(400, f"Maximálně {PROPHECY_MAX_ACTIVE} aktivních svitků najednou.")

    scroll = ProphecyScroll.create(
        creator_char_id=char.id,
        quest_def_id=req.quest_def_id,
        prediction_type=req.prediction_type,
        prediction_value=req.prediction_value,
        price=req.price,
    )
    db.add(scroll)

    xp_result = await award_xp(char.id, "oracle", PROPHECY_XP["create"], db)
    scroll.xp_create_awarded = True

    await db.commit()
    await db.refresh(scroll)

    return {
        "message":   "Svitek proroctví vytvořen a nabídnut na burze.",
        "scroll":    scroll.to_dict(for_buyer=True),
        "xp_result": xp_result,
    }


@router.post("/buy")
async def buy_scroll(
    req:  BuyScrollRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Koupí svitek proroctví. Kupující uvidí konkrétní předpověď.
    XP za prodej obdrží Věštec.
    """
    char = await get_char(user, db)

    scroll_res = await db.execute(
        select(ProphecyScroll)
        .options(selectinload(ProphecyScroll.creator))
        .where(ProphecyScroll.id == req.scroll_id)
    )
    scroll = scroll_res.scalar_one_or_none()
    if not scroll:
        raise HTTPException(404, "Svitek nenalezen.")
    if not scroll.is_available:
        raise HTTPException(400, "Tento svitek již není dostupný (prodán nebo expiroval).")
    if scroll.creator_char_id == char.id:
        raise HTTPException(400, "Nemůžeš koupit vlastní svitek.")
    if char.gold < scroll.price:
        raise HTTPException(400, f"Nedostatek zlata. Potřebuješ {scroll.price} G.")

    # Transakce
    char.gold -= scroll.price
    await log_gold(db, char, -scroll.price, GoldReason.DIVINER_PURCHASE,
                   {"scroll_id": scroll.id})

    creator_res = await db.execute(
        select(Character).where(Character.id == scroll.creator_char_id)
    )
    creator = creator_res.scalar_one_or_none()
    if creator:
        creator.gold += scroll.price
        await log_gold(db, creator, scroll.price, GoldReason.DIVINER_SALE,
                       {"scroll_id": scroll.id})

    scroll.sold_to_char_id = char.id
    scroll.sold_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # XP Věštci za prodej
    if not scroll.xp_sold_awarded:
        await award_xp(scroll.creator_char_id, "oracle", PROPHECY_XP["sold"], db)
        scroll.xp_sold_awarded = True

    await db.commit()

    return {
        "message":          "Svitek koupen! Předpověď odhalena.",
        "prediction_type":  scroll.prediction_type,
        "prediction_value": scroll.prediction_value,
        "quest_def_id":     scroll.quest_def_id,
        "scroll":           scroll.to_dict(for_buyer=True),
        "gold_spent":       scroll.price,
    }


@router.get("/accuracy")
async def weekly_accuracy(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Týdenní accuracy statistiky pro XP bonus.
    Bonus se uděluje automaticky každý týden (zde jen zobrazení stavu).
    """
    char = await get_char(user, db)
    await require_active_profession(char.id, "oracle", db)

    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    result = await db.execute(
        select(ProphecyScroll).where(
            ProphecyScroll.creator_char_id == char.id,
            ProphecyScroll.is_verified == True,
            ProphecyScroll.verified_at >= week_ago,
        )
    )
    week_scrolls = result.scalars().all()

    correct  = [s for s in week_scrolls if s.was_correct]
    accuracy = round(len(correct) / len(week_scrolls) * 100, 1) if week_scrolls else 0.0

    bonus_xp = 0
    if accuracy >= 90:
        bonus_xp = PROPHECY_XP["weekly_90pct"]
    elif accuracy >= 70:
        bonus_xp = PROPHECY_XP["weekly_70pct"]

    return {
        "week_verified":   len(week_scrolls),
        "week_correct":    len(correct),
        "accuracy_pct":    accuracy,
        "bonus_xp_earned": bonus_xp,
        "thresholds": {
            "70pct": PROPHECY_XP["weekly_70pct"],
            "90pct": PROPHECY_XP["weekly_90pct"],
        },
    }


# ── Interní hook (volá se z quest collect) ───────────────────────────────────

async def verify_prophecies_for_quest(
    quest_def_id: int,
    actual_success: bool,
    actual_rarity:  str | None,
    db: AsyncSession,
) -> None:
    """
    Verifikuje všechny koupené svitky pro daný quest po jeho dokončení.
    Volá se z routers/quest.py → collect().
    XP se přičte tvůrci automaticky.
    """
    result = await db.execute(
        select(ProphecyScroll).where(
            ProphecyScroll.quest_def_id == quest_def_id,
            ProphecyScroll.sold_to_char_id != None,
            ProphecyScroll.is_verified == False,
        )
    )
    scrolls = result.scalars().all()

    for scroll in scrolls:
        was_correct = False
        if scroll.prediction_type == "quest_success":
            expected = "success" if actual_success else "fail"
            was_correct = scroll.prediction_value == expected
        elif scroll.prediction_type == "quest_drop_rarity" and actual_rarity:
            was_correct = scroll.prediction_value == actual_rarity

        scroll.is_verified = True
        scroll.was_correct = was_correct
        scroll.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)

        if not scroll.xp_result_awarded:
            xp = PROPHECY_XP["correct"] if was_correct else PROPHECY_XP["wrong"]
            if xp > 0:
                await award_xp(scroll.creator_char_id, "oracle", xp, db)
            scroll.xp_result_awarded = True
