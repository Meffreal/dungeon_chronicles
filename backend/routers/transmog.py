"""
routers/transmog.py — Transmog systém.

Endpointy:
  GET  /transmog/           — všechny aktivní transmoogy hráče
  GET  /transmog/options    — inventář itemů použitelných jako transmog (dle slotu)
  POST /transmog/set        — nastav kosmetický vzhled slotu (costs 100 gold)
  POST /transmog/clear      — vymaž transmog pro jeden slot (free)
  POST /transmog/clear-all  — vymaž všechny transmoogy (free)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.item import Item, InventoryItem
from models.transmog import TransmogSlot, TRANSMOG_COST, VALID_SLOTS
from models.economy import log_gold, GoldReason
from routers.auth import get_current_user

router = APIRouter(prefix="/transmog", tags=["transmog"])


async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def get_transmog_dict(character_id: int, db: AsyncSession) -> dict:
    """
    Vrátí dict slot → item_dict pro všechny aktivní transmoogy postavy.
    Používá se v char_dict_with_equipment.
    """
    result = await db.execute(
        select(TransmogSlot)
        .options(selectinload(TransmogSlot.cosmetic_item))
        .where(TransmogSlot.character_id == character_id)
    )
    rows = result.scalars().all()
    out = {}
    for row in rows:
        if row.cosmetic_item:
            out[row.slot] = row.cosmetic_item.to_dict()
    return out


# ── GET /transmog/ ─────────────────────────────────────────────────────────────

@router.get("/")
async def get_transmogs(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vrátí aktivní transmoogy přihlášeného hráče."""
    char = await _get_char(user, db)
    transmogs = await get_transmog_dict(char.id, db)
    return {"transmogs": transmogs, "cost_per_slot": TRANSMOG_COST}


# ── GET /transmog/options ──────────────────────────────────────────────────────

@router.get("/options")
async def get_transmog_options(
    slot: str,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Vrátí inventář hráče filtrovaný na daný slot type —
    tyto itemy může hráč použít jako transmog pro daný slot.
    """
    if slot not in VALID_SLOTS:
        raise HTTPException(400, f"Neplatný slot. Možnosti: {sorted(VALID_SLOTS)}")

    char = await _get_char(user, db)

    # Inventář hráče — itemy daného typu
    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.character_id == char.id)
    )
    inv_items = result.scalars().all()

    options = []
    for inv in inv_items:
        if inv.item and inv.item.item_type == slot:
            d = inv.to_dict()
            d["is_equipped"] = getattr(char, f"eq_{slot}") == inv.item_id
            options.append(d)

    # Aktuální transmog pro tento slot
    tmog_result = await db.execute(
        select(TransmogSlot)
        .options(selectinload(TransmogSlot.cosmetic_item))
        .where(TransmogSlot.character_id == char.id, TransmogSlot.slot == slot)
    )
    current_tmog = tmog_result.scalar_one_or_none()

    return {
        "slot":           slot,
        "options":        options,
        "current_transmog": current_tmog.cosmetic_item.to_dict() if (current_tmog and current_tmog.cosmetic_item) else None,
        "cost":           TRANSMOG_COST,
    }


# ── POST /transmog/set ────────────────────────────────────────────────────────

class SetTransmogRequest(BaseModel):
    slot:              str
    cosmetic_item_id:  int   # ID z tabulky items (ne inventory)


@router.post("/set")
async def set_transmog(
    req: SetTransmogRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Nastav kosmetický vzhled pro slot.
    - Hráč musí mít item v inventáři
    - Item musí být stejného type jako slot
    - Stojí 100 gold
    """
    if req.slot not in VALID_SLOTS:
        raise HTTPException(400, f"Neplatný slot. Možnosti: {sorted(VALID_SLOTS)}")

    char = await _get_char(user, db)

    # Zkontroluj, že hráč má daný item v inventáři
    inv_result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(
            InventoryItem.character_id == char.id,
            InventoryItem.item_id == req.cosmetic_item_id,
        )
    )
    inv_item = inv_result.scalar_one_or_none()
    if not inv_item or not inv_item.item:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    # Ověř správný typ
    if inv_item.item.item_type != req.slot:
        raise HTTPException(400, f"Item '{inv_item.item.name}' je typ '{inv_item.item.item_type}', ale slot '{req.slot}' očekává jiný typ.")

    # Ověř gold
    if char.gold < TRANSMOG_COST:
        raise HTTPException(400, f"Nedostatek goldu. Transmog stojí {TRANSMOG_COST} G.")

    # Odpočítej gold
    char.gold -= TRANSMOG_COST
    await log_gold(db, char, -TRANSMOG_COST, GoldReason.TRANSMOG_FEE,
                   {"action": "transmog_set", "slot": req.slot, "item_id": req.cosmetic_item_id})

    # Nastav nebo aktualizuj transmog slot
    existing_result = await db.execute(
        select(TransmogSlot).where(
            TransmogSlot.character_id == char.id,
            TransmogSlot.slot == req.slot,
        )
    )
    existing = existing_result.scalar_one_or_none()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing:
        existing.cosmetic_item_id = req.cosmetic_item_id
        existing.applied_at = now
    else:
        db.add(TransmogSlot(
            character_id=char.id,
            slot=req.slot,
            cosmetic_item_id=req.cosmetic_item_id,
            applied_at=now,
        ))

    await db.commit()

    return {
        "message":    f"Transmog nastaven pro slot '{req.slot}'.",
        "item_name":  inv_item.item.name,
        "gold_spent": TRANSMOG_COST,
        "gold_left":  char.gold,
    }


# ── POST /transmog/clear ──────────────────────────────────────────────────────

class ClearTransmogRequest(BaseModel):
    slot: str


@router.post("/clear")
async def clear_transmog(
    req: ClearTransmogRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vymaže transmog pro jeden slot (zdarma)."""
    if req.slot not in VALID_SLOTS:
        raise HTTPException(400, f"Neplatný slot.")

    char = await _get_char(user, db)

    result = await db.execute(
        select(TransmogSlot).where(
            TransmogSlot.character_id == char.id,
            TransmogSlot.slot == req.slot,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"message": "Žádný transmog pro tento slot."}

    await db.delete(row)
    await db.commit()
    return {"message": f"Transmog pro slot '{req.slot}' odstraněn."}


# ── POST /transmog/clear-all ──────────────────────────────────────────────────

@router.post("/clear-all")
async def clear_all_transmogs(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Vymaže všechny transmoogy hráče (zdarma)."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(TransmogSlot).where(TransmogSlot.character_id == char.id)
    )
    rows = result.scalars().all()
    count = len(rows)
    for row in rows:
        await db.delete(row)

    await db.commit()
    return {"message": f"Odstraněno {count} transmog{'ů' if count != 1 else ''}.", "cleared": count}
