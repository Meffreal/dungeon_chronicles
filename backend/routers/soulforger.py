"""
routers/soulforger.py — Dušekoval: forge operace, sloty, historie
"""
import json
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.item import Item, InventoryItem
from models.soulforger import (
    ForgeLog, FORGE_SLOT_COUNT, FORGE_COOLDOWN_HOURS,
    FORGE_XP, FORGE_FAIL_CHANCE, FORGE_SALE_BONUS_MULTIPLIER,
)
from game.professions import (
    get_char, require_active_profession, award_xp, generate_forge_name,
)
from routers.auth import get_current_user

router = APIRouter(prefix="/soulforger", tags=["soulforger"])

# Kolik vstupních itemů je potřeba pro forge (min / max)
FORGE_INPUT_MIN = 2
FORGE_INPUT_MAX = 4


# ── Schemas ───────────────────────────────────────────────────────────────────

class ForgeRequest(BaseModel):
    inventory_item_ids: list[int]   # 2–4 IDs z inventáře
    target_type: str                # weapon | helmet | armor | gloves | boots | ring | amulet


# ── Helpery ───────────────────────────────────────────────────────────────────

RARITY_WEIGHT = {
    "common":    1,
    "uncommon":  2,
    "rare":      3,
    "epic":      5,
    "legendary": 8,
    "set":       4,
}

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "legendary"]


def _calculate_output_rarity(input_rarities: list[str]) -> str:
    """
    Výstupní rarity závisí na vstupech.
    Průměrná váha + náhoda (+/- 1 tier).
    """
    weights = [RARITY_WEIGHT.get(r, 1) for r in input_rarities]
    avg = sum(weights) / len(weights)

    # Normalizuj na index v RARITY_ORDER
    idx = min(4, max(0, int(avg) - 1))
    # Náhoda: ±1 tier
    roll = random.random()
    if roll > 0.75 and idx < 4:
        idx += 1
    elif roll < 0.20 and idx > 0:
        idx -= 1

    return RARITY_ORDER[idx]


async def _get_free_forge_slot(char_id: int, db: AsyncSession) -> int:
    """Vrátí číslo volného forge slotu (0–2) nebo -1 pokud jsou všechny obsazené."""
    result = await db.execute(
        select(ForgeLog)
        .where(ForgeLog.crafter_char_id == char_id)
        .order_by(ForgeLog.created_at.desc())
        .limit(FORGE_SLOT_COUNT * 2)
    )
    recent = result.scalars().all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    occupied = set()
    for log in recent:
        available_at = log.slot_available_at
        if now < available_at:
            occupied.add(log.forge_slot)

    for slot in range(FORGE_SLOT_COUNT):
        if slot not in occupied:
            return slot
    return -1


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/slots")
async def forge_slots(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Stav forge slotů — které jsou dostupné, které čekají na cooldown."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "runist", db)

    result = await db.execute(
        select(ForgeLog)
        .where(ForgeLog.crafter_char_id == char.id)
        .order_by(ForgeLog.created_at.desc())
        .limit(FORGE_SLOT_COUNT * 2)
    )
    recent = result.scalars().all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    slots = []
    last_per_slot: dict[int, ForgeLog] = {}
    for log in recent:
        if log.forge_slot not in last_per_slot:
            last_per_slot[log.forge_slot] = log

    for slot in range(FORGE_SLOT_COUNT):
        log = last_per_slot.get(slot)
        if log:
            available_at = log.slot_available_at
            available = now >= available_at
        else:
            available = True
            available_at = None

        slots.append({
            "slot":         slot,
            "available":    available,
            "available_at": available_at.isoformat() if available_at and not available else None,
            "last_forge":   log.to_dict() if log else None,
        })

    return {"slots": slots}


@router.get("/history")
async def forge_history(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Posledních 20 forge operací."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "runist", db)

    result = await db.execute(
        select(ForgeLog)
        .options(selectinload(ForgeLog.output_item))
        .where(ForgeLog.crafter_char_id == char.id)
        .order_by(ForgeLog.created_at.desc())
        .limit(20)
    )
    logs = result.scalars().all()
    return {"history": [l.to_dict() for l in logs]}


@router.post("/forge")
async def forge_items(
    req:  ForgeRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Hlavní forge endpoint. Zničí 2–4 inventory itemů a vytvoří nový.
    Výsledná rarity závisí na vstupech + náhoda.
    Při neúspěchu jsou itemy stále zničeny — risk je součástí designu.
    """
    char = await get_char(user, db)
    prof = await require_active_profession(char.id, "runist", db)

    # Validace počtu vstupů
    ids = list(set(req.inventory_item_ids))   # deduplikace
    if len(ids) < FORGE_INPUT_MIN:
        raise HTTPException(400, f"Potřebuješ alespoň {FORGE_INPUT_MIN} různé předměty.")
    if len(ids) > FORGE_INPUT_MAX:
        raise HTTPException(400, f"Maximálně {FORGE_INPUT_MAX} předměty najednou.")

    # Cílový typ předmětu
    valid_types = ["weapon", "helmet", "armor", "gloves", "boots", "ring", "amulet"]
    if req.target_type not in valid_types:
        raise HTTPException(400, f"Neplatný typ. Možnosti: {valid_types}")

    # Volný forge slot
    slot = await _get_free_forge_slot(char.id, db)
    if slot == -1:
        raise HTTPException(400, f"Všechny forge sloty jsou obsazeny. Čekej na cooldown ({FORGE_COOLDOWN_HOURS}h).")

    # Načti a ověř všechny vstupy
    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(
            InventoryItem.id.in_(ids),
            InventoryItem.character_id == char.id,
        )
    )
    inv_items = inv_res.scalars().all()
    if len(inv_items) != len(ids):
        raise HTTPException(404, "Některé předměty nebyly nalezeny v tvém inventáři.")

    # Zkontroluj že nejsou nasazeny
    equipped_item_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    }
    for inv in inv_items:
        if inv.item_id in equipped_item_ids:
            raise HTTPException(400, f"Předmět '{inv.item.name}' je nasazen. Nejdřív ho sundej.")

    input_rarities = [inv.item.rarity for inv in inv_items]

    # Výpočet výstupní rarity
    output_rarity = _calculate_output_rarity(input_rarities)

    # Šance na selhání (klesá s rankem)
    fail_chance = FORGE_FAIL_CHANCE[min(prof.rank, len(FORGE_FAIL_CHANCE) - 1)]
    success = random.random() > fail_chance

    # Zniš vstupní itemy
    inv_ids_json = json.dumps(ids)
    rarities_json = json.dumps(input_rarities)
    for inv in inv_items:
        await db.delete(inv)

    output_item_id = None
    output_name    = None
    output_flavor  = None

    if success:
        # Najdi item odpovídající rarity a typu z DB
        item_res = await db.execute(
            select(Item).where(
                Item.item_type == req.target_type,
                Item.rarity == output_rarity,
            )
        )
        candidates = item_res.scalars().all()
        base_item = random.choice(candidates) if candidates else None

        if base_item:
            output_item_id = base_item.id
            output_name, output_flavor = generate_forge_name(req.target_type, output_rarity)

            # Přidej do inventáře
            new_inv = InventoryItem(
                character_id=char.id,
                item_id=base_item.id,
                quantity=1,
            )
            db.add(new_inv)

    # Ulož log
    base_xp = FORGE_XP.get(output_rarity, 30) if success else 0
    log = ForgeLog(
        crafter_char_id=char.id,
        input_inv_ids_json=inv_ids_json,
        input_rarities_json=rarities_json,
        output_item_id=output_item_id,
        output_rarity=output_rarity if success else None,
        output_name=output_name,
        output_flavor=output_flavor,
        success=success,
        forge_slot=slot,
        base_xp=base_xp,
    )
    db.add(log)

    # XP
    xp_result = {"awarded": False}
    if success and base_xp > 0:
        xp_result = await award_xp(char.id, "runist", base_xp, db)
        log.base_xp_awarded = True

    await db.commit()

    return {
        "success":       success,
        "output_rarity": output_rarity if success else None,
        "output_name":   output_name,
        "output_flavor": output_flavor,
        "inputs_destroyed": len(ids),
        "forge_slot":    slot,
        "available_at":  (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=FORGE_COOLDOWN_HOURS)).isoformat(),
        "xp_result":     xp_result,
        "message": (
            f"Forge úspěšný! Vznikl {output_rarity} předmět: '{output_name}'."
            if success else
            "Forge selhal. Materiály byly pohlceny. Zkus to znovu."
        ),
    }


# ── Interní hook: retroaktivní XP za prodej forged itemu ─────────────────────

async def on_forged_item_sold(item_id: int, db: AsyncSession) -> None:
    """
    Volá se z market.py při prodeji itemu.
    Pokud byl item forged, přidá Dušekovalovi retroaktivní XP bonus.
    """
    result = await db.execute(
        select(ForgeLog).where(
            ForgeLog.output_item_id == item_id,
            ForgeLog.sale_bonus_xp_awarded == False,
            ForgeLog.success == True,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        return

    bonus = int(log.base_xp * FORGE_SALE_BONUS_MULTIPLIER)
    if bonus > 0:
        await award_xp(log.crafter_char_id, "runist", bonus, db)
    log.sale_bonus_xp_awarded = True
