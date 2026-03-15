"""
routers/runosmith.py — Runovník: runy, inscripce, evoluce, reforge
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.item import InventoryItem
from models.runosmith import (
    Rune, ItemRune,
    RUNE_COMBINATION_LOOKUP, MAX_RUNES_PER_ITEM, RUNE_XP_COOLDOWN_HOURS,
)
from models.runosmith import RUNE_DEFINITIONS
from game.professions import (
    get_char, require_active_profession, require_active_profession_rank, award_xp,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/runosmith", tags=["runosmith"])

RUNOSMITH_XP = {
    "inscribe_own":    20,
    "inscribe_other":  40,
    "evolve":         150,
    "combination_new": 500,   # první kombinace tohoto typu na serveru
    "remove_rune":      0,    # reforge nedává XP
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class InscribeRequest(BaseModel):
    inventory_item_id: int
    rune_id:           int
    slot:              int = 1    # 1 nebo 2

class RemoveRequest(BaseModel):
    item_rune_id: int


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_inv_item(inv_id: int, char_id: int, db: AsyncSession) -> InventoryItem:
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.id == inv_id, InventoryItem.character_id == char_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Předmět nenalezen v inventáři.")
    return inv


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/runes")
async def list_available_runes(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vrátí všechny runy dostupné pro aktuální rank Runovníka.
    Runy vyššího tieru jsou vidět, ale označeny jako locked.
    """
    char = await get_char(user, db)
    prof = await require_active_profession(char.id, "runist", db)

    result = await db.execute(select(Rune).order_by(Rune.tier, Rune.id))
    runes  = result.scalars().all()

    return {
        "runes": [
            {**r.to_dict(), "available": r.rank_required <= prof.rank}
            for r in runes
        ],
        "your_rank": prof.rank,
    }


@router.get("/item/{inv_item_id}")
async def item_runes(
    inv_item_id: int,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vrátí runy inscribované na konkrétním předmětu v inventáři."""
    char = await get_char(user, db)
    await _get_inv_item(inv_item_id, char.id, db)   # ověření vlastnictví

    result = await db.execute(
        select(ItemRune)
        .options(selectinload(ItemRune.rune))
        .where(ItemRune.inventory_item_id == inv_item_id)
        .order_by(ItemRune.slot)
    )
    runes = result.scalars().all()
    return {"runes": [r.to_dict() for r in runes]}


@router.post("/inscribe")
async def inscribe_rune(
    req:  InscribeRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Inscribuje runu na předmět. Slot 2 je dostupný od Rank 3.
    Při dvou runách systém vyhodnotí kombinaci (synergy / conflict).
    XP bonus pokud inscribuješ na předmět JINÉHO hráče (service economy).
    """
    char = await get_char(user, db)
    prof = await require_active_profession(char.id, "runist", db)

    # Načti cílový předmět
    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.id == req.inventory_item_id)
    )
    inv_item = inv_res.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Předmět nenalezen.")

    is_own = (inv_item.character_id == char.id)

    # Slot 2 vyžaduje Rank 3
    if req.slot == 2 and prof.rank < 3:
        raise HTTPException(403, "Druhý slot runy odemkneš na Rank 3.")
    if req.slot not in (1, 2):
        raise HTTPException(400, "Slot musí být 1 nebo 2.")

    # Načti runu
    rune_res = await db.execute(select(Rune).where(Rune.id == req.rune_id))
    rune = rune_res.scalar_one_or_none()
    if not rune:
        raise HTTPException(404, "Runa nenalezena.")
    if rune.rank_required > prof.rank:
        raise HTTPException(403, f"Tato runa vyžaduje Rank {rune.rank_required}. Ty jsi Rank {prof.rank}.")

    # Zkontroluj jestli slot není obsazen
    existing_res = await db.execute(
        select(ItemRune).where(
            ItemRune.inventory_item_id == req.inventory_item_id,
            ItemRune.slot == req.slot,
        )
    )
    if existing_res.scalar_one_or_none():
        raise HTTPException(400, f"Slot {req.slot} je již obsazen. Nejdřív runu odstraň.")

    # Vyhodnoť kombinaci pokud je tam druhý slot obsazen
    combination_type = None
    combination_desc = None
    if req.slot == 2:
        other_slot_res = await db.execute(
            select(ItemRune)
            .options(selectinload(ItemRune.rune))
            .where(
                ItemRune.inventory_item_id == req.inventory_item_id,
                ItemRune.slot == 1,
            )
        )
        other = other_slot_res.scalar_one_or_none()
        if other and other.rune:
            combo = RUNE_COMBINATION_LOOKUP.get((other.rune.key, rune.key))
            if combo:
                combination_type = combo["type"]
                combination_desc = combo["description"]
                # Aktualizuj i první runu
                other.combination_type = combination_type

    # Vlož runu
    item_rune = ItemRune(
        inventory_item_id=req.inventory_item_id,
        rune_id=rune.id,
        slot=req.slot,
        inscribed_by_char_id=char.id,
        combination_type=combination_type,
        last_xp_awarded_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(item_rune)

    # XP
    xp_amount = RUNOSMITH_XP["inscribe_other"] if not is_own else RUNOSMITH_XP["inscribe_own"]
    xp_result = await award_xp(char.id, "runist", xp_amount, db)

    await db.commit()
    await db.refresh(item_rune)

    return {
        "message":          f"Runa '{rune.name}' inscribována do slotu {req.slot}.",
        "item_rune":        item_rune.to_dict(),
        "combination_type": combination_type,
        "combination_desc": combination_desc,
        "xp_result":        xp_result,
    }


@router.post("/evolve/{item_rune_id}")
async def evolve_rune(
    item_rune_id: int,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Pokusí se evolvovat runu na předmětu pokud má dostatek rezonance.
    Runa se nahradí vyšší verzí (stejný slot, vynulovaná rezonance).
    """
    char = await get_char(user, db)
    await require_active_profession(char.id, "runist", db)

    ir_res = await db.execute(
        select(ItemRune)
        .options(selectinload(ItemRune.rune), selectinload(ItemRune.inventory_item))
        .where(ItemRune.id == item_rune_id)
    )
    ir = ir_res.scalar_one_or_none()
    if not ir:
        raise HTTPException(404, "ItemRune nenalezena.")

    # Ověř vlastnictví předmětu
    if ir.inventory_item.character_id != char.id and ir.inscribed_by_char_id != char.id:
        raise HTTPException(403, "Tato runa není tvoje.")

    rune = ir.rune
    if not rune or not rune.evolves_to or not rune.resonance_to_evolve:
        raise HTTPException(400, "Tato runa nemá vyšší verzi.")
    if ir.resonance < rune.resonance_to_evolve:
        raise HTTPException(400,
            f"Nedostatečná rezonance. Máš {ir.resonance}, potřebuješ {rune.resonance_to_evolve}."
        )

    # Načti cílovou runu
    new_rune_res = await db.execute(select(Rune).where(Rune.key == rune.evolves_to))
    new_rune = new_rune_res.scalar_one_or_none()
    if not new_rune:
        raise HTTPException(500, "Cílová runa nenalezena — kontaktuj administrátora.")

    old_name = rune.name
    ir.rune_id   = new_rune.id
    ir.resonance = 0    # reset po evolve
    ir.combination_type = None  # kombinace se musí přepočítat

    xp_result = await award_xp(char.id, "runist", RUNOSMITH_XP["evolve"], db)
    await db.commit()
    await db.refresh(ir)

    return {
        "message":    f"'{old_name}' evolvovala na '{new_rune.name}'!",
        "item_rune":  ir.to_dict(),
        "xp_result":  xp_result,
    }


@router.delete("/remove")
async def remove_rune(
    req:  RemoveRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Odstraní runu z předmětu (Rank 4+). Nedává XP.
    Combinační efekt druhé runy se resetuje.
    """
    char = await get_char(user, db)
    await require_active_profession_rank(char.id, "runist", 4, db)

    ir_res = await db.execute(
        select(ItemRune)
        .options(selectinload(ItemRune.inventory_item))
        .where(ItemRune.id == req.item_rune_id)
    )
    ir = ir_res.scalar_one_or_none()
    if not ir:
        raise HTTPException(404, "ItemRune nenalezena.")
    if ir.inventory_item.character_id != char.id:
        raise HTTPException(403, "Tento předmět není tvůj.")

    # Resetuj kombinaci na druhém slotu
    other_slot = 2 if ir.slot == 1 else 1
    other_res = await db.execute(
        select(ItemRune).where(
            ItemRune.inventory_item_id == ir.inventory_item_id,
            ItemRune.slot == other_slot,
        )
    )
    other = other_res.scalar_one_or_none()
    if other:
        other.combination_type = None

    await db.delete(ir)
    await db.commit()
    return {"message": "Runa odstraněna. Předmět je nyní čistý."}
