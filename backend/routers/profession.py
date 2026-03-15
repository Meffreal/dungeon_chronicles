"""
routers/profession.py — Správa profesí: learn, activate, deactivate, přehled
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from database import get_db
from models.economy import log_gold, GoldReason
from models.user import User
from models.character import Character
from models.profession import (
    CharacterProfession, PROFESSION_KEYS, PROFESSION_META,
    PROFESSION_LEARN_COSTS, ACTIVE_SLOTS,
)
from game.professions import get_char, learn_cost_for_char, get_free_slot
from routers.auth import get_current_user

router = APIRouter(prefix="/professions", tags=["professions"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LearnRequest(BaseModel):
    profession_key: str

class ActivateRequest(BaseModel):
    profession_key: str   # co chceme aktivovat
    replace_slot:   int   # slot 1 nebo 2 — kterou profesi nahradíme


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/")
async def list_professions(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vrátí přehled všech profesí s jejich stavem pro aktuálního hráče:
    - learned / active / available (nenaučená)
    - rank, XP, cooldown slotu
    - cena za naučení další profese
    """
    char = await get_char(user, db)

    result = await db.execute(
        select(CharacterProfession).where(CharacterProfession.character_id == char.id)
    )
    learned = {p.profession_key: p for p in result.scalars().all()}

    next_cost = await learn_cost_for_char(char.id, db)

    professions = []
    for key in PROFESSION_KEYS:
        meta = PROFESSION_META[key]
        if key in learned:
            p = learned[key]
            professions.append({
                **p.to_dict(),
                "status": "active" if p.is_active else "learned",
            })
        else:
            professions.append({
                "profession_key": key,
                "name":          meta["name"],
                "icon":          meta["icon"],
                "description":   meta["description"],
                "status":        "available",
                "rank":          0,
                "xp":            0,
                "xp_to_next":    None,
                "is_active":     False,
                "slot":          None,
                "can_deactivate":False,
                "slot_locked_until": None,
                "learned_at":    None,
                "karma_points":  0,
            })

    return {
        "professions":     professions,
        "active_slots":    ACTIVE_SLOTS,
        "learned_count":   len(learned),
        "next_learn_cost": next_cost,    # -1 pokud má všechny
        "gold":            char.gold,
    }


@router.post("/learn")
async def learn_profession(
    req: LearnRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Naučí hráče novou profesi.
    - 1. a 2. profese jsou zdarma a automaticky se aktivují.
    - 3.–6. profese stojí zlato a jdou do dormant stavu.
    """
    char = await get_char(user, db)

    if req.profession_key not in PROFESSION_KEYS:
        raise HTTPException(400, f"Neznámá profese '{req.profession_key}'.")

    # Zkontroluj zda ji hráč už nemá
    existing = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char.id,
            CharacterProfession.profession_key == req.profession_key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Tuto profesi už znáš.")

    cost = await learn_cost_for_char(char.id, db)
    if cost == -1:
        raise HTTPException(400, "Znáš již všechny profese.")
    if char.gold < cost:
        raise HTTPException(400, f"Nedostatek zlata. Potřebuješ {cost} G, máš {char.gold} G.")

    # Strhni zlato
    char.gold -= cost
    await log_gold(db, char, -cost, GoldReason.PROFESSION_LEARN,
                   {"profession": req.profession_type})
    gold_remaining = char.gold  # zachyť před commitem — po commitu jsou atributy expirované

    # Zjisti volný slot (první dvě profese se auto-aktivují)
    free_slot = await get_free_slot(char.id, db)
    auto_activate = free_slot is not None

    prof = CharacterProfession(
        character_id=char.id,
        profession_key=req.profession_key,
        is_active=auto_activate,
        slot=free_slot if auto_activate else None,
        activated_at=datetime.now(timezone.utc).replace(tzinfo=None) if auto_activate else None,
    )
    db.add(prof)
    await db.commit()
    await db.refresh(prof)

    meta = PROFESSION_META[req.profession_key]
    return {
        "message":      f"Naučil ses profesi '{meta['name']}'!",
        "auto_activated": auto_activate,
        "slot":         free_slot,
        "gold_spent":   cost,
        "gold_remaining": gold_remaining,
        "profession":   prof.to_dict(),
    }


@router.post("/activate")
async def activate_profession(
    req: ActivateRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Aktivuje dormant profesi do zvoleného slotu (1 nebo 2).
    Profese aktuálně v daném slotu půjde do dormant.
    Cooldown: profesi v cílovém slotu nelze deaktivovat dřív než 48h po poslední aktivaci.
    """
    char = await get_char(user, db)

    if req.replace_slot not in (1, 2):
        raise HTTPException(400, "Slot musí být 1 nebo 2.")

    # Načti profesi k aktivaci
    new_result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char.id,
            CharacterProfession.profession_key == req.profession_key,
        )
    )
    new_prof = new_result.scalar_one_or_none()
    if not new_prof:
        raise HTTPException(400, "Tuto profesi ještě neznáš.")
    if new_prof.is_active:
        raise HTTPException(400, "Tato profese je již aktivní.")

    # Načti profesi aktuálně v cílovém slotu
    old_result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char.id,
            CharacterProfession.slot == req.replace_slot,
        )
    )
    old_prof = old_result.scalar_one_or_none()

    deactivated_key = None
    if old_prof:
        if not old_prof.can_deactivate:
            until = old_prof.slot_locked_until
            raise HTTPException(400,
                f"Profesi '{old_prof.profession_key}' nelze ještě deaktivovat. "
                f"Cooldown vyprší v {until.isoformat() if until else '?'}."
            )
        # Zachyť klíč před commitem — po commitu jsou atributy expirované
        deactivated_key = old_prof.profession_key
        # Přesuň do dormant
        old_prof.is_active = False
        old_prof.slot = None

    # Aktivuj novou profesi
    new_prof.is_active = True
    new_prof.slot = req.replace_slot
    new_prof.activated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(new_prof)

    meta = PROFESSION_META[req.profession_key]
    return {
        "message":    f"Profese '{meta['name']}' aktivována v slotu {req.replace_slot}.",
        "deactivated": deactivated_key,
        "profession": new_prof.to_dict(),
    }


@router.get("/active")
async def my_active_professions(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Rychlý přehled obou aktivních profesí a jejich rankü."""
    char = await get_char(user, db)
    result = await db.execute(
        select(CharacterProfession).where(
            CharacterProfession.character_id == char.id,
            CharacterProfession.is_active == True,
        )
    )
    active = result.scalars().all()
    return {"active_professions": [p.to_dict() for p in active]}
