"""
routers/inventory.py — Inventář, equip/unequip, prodej do shopu
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character, xp_to_next
from models.item import Item, InventoryItem, Rarity, RARITY_COLOR
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/inventory", tags=["inventory"])

SLOT_MAP = {
    "weapon": "eq_weapon",
    "helmet": "eq_helmet",
    "armor":  "eq_armor",
    "gloves": "eq_gloves",
    "boots":  "eq_boots",
    "ring":   "eq_ring",
    "amulet": "eq_amulet",
}

# ── Schemas ───────────────────────────────────────────────────────────────────
class EquipRequest(BaseModel):
    inv_item_id: int   # ID záznamu v tabulce inventory (ne item.id)

class UnequipRequest(BaseModel):
    slot: str          # weapon / helmet / armor / ...

class SellRequest(BaseModel):
    inv_item_id: int
    quantity: int = 1

# ── Helper ────────────────────────────────────────────────────────────────────
async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char

def _apply_equipment_bonuses(char: Character, items: list[Item]):
    """Přičte bonusy všech nasazených itemů ke stats postavy."""
    char.recalculate_stats()   # základ bez equipu
    for item in items:
        if item is None:
            continue
        char.atk   += item.bonus_atk
        char.def_  += item.bonus_def
        char.spd   += item.bonus_spd
        char.hp_max += item.bonus_hp
        char.mp_max += item.bonus_mp
        # Primary stats — ty se propíší přes recalculate
        char.strength     += item.bonus_str
        char.dexterity    += item.bonus_dex
        char.intelligence += item.bonus_int
        char.endurance    += item.bonus_end
        char.luck         += item.bonus_luck

async def recalculate_with_gear(char: Character, db: AsyncSession):
    """Přepočítá stats postavy včetně všech nasazených itemů."""
    char.recalculate_stats()

    # Načti všechny nasazené itemy
    eq_ids = [
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    ]
    equipped_items = []
    for item_id in eq_ids:
        if item_id is not None:
            res = await db.execute(select(Item).where(Item.id == item_id))
            item = res.scalar_one_or_none()
            if item:
                equipped_items.append(item)

    _apply_equipment_bonuses(char, equipped_items)

# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/")
async def get_inventory(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí celý inventář postavy."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.character_id == char.id)
        .order_by(InventoryItem.item_id)
    )
    inv = result.scalars().all()

    # Které item IDs jsou nasazeny
    equipped_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    } - {None}

    items = []
    for inv_item in inv:
        d = inv_item.to_dict()
        d["equipped"] = inv_item.item_id in equipped_ids
        # Zjisti ve kterém slotu je nasazen
        d["equipped_in"] = None
        if inv_item.item_id in equipped_ids:
            for slot, attr in SLOT_MAP.items():
                if getattr(char, attr) == inv_item.item_id:
                    d["equipped_in"] = slot
                    break
        items.append(d)

    return {"items": items, "count": len(items)}


@router.post("/equip")
async def equip_item(
    req: EquipRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nasadí item z inventáře do příslušného slotu."""
    char = await _get_char(user, db)

    # Najdi inventory záznam
    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(
            InventoryItem.id == req.inv_item_id,
            InventoryItem.character_id == char.id,
        )
    )
    inv_item = inv_res.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item = inv_item.item
    if not item:
        raise HTTPException(404, "Item data nenalezena.")

    # Zkontroluj typ → slot
    slot_attr = SLOT_MAP.get(item.item_type)
    if not slot_attr:
        raise HTTPException(400, f"Typ '{item.item_type}' nelze nasadit.")

    if item.min_level > char.level:
        raise HTTPException(400, f"Potřebuješ level {item.min_level} pro tento item.")

    # Nasaď (případný starý item zůstane v inventáři automaticky)
    setattr(char, slot_attr, item.id)

    # Přepočítej stats
    await recalculate_with_gear(char, db)
    await db.commit()
    await db.refresh(char)

    return {
        "message": f"'{item.name}' nasazen do slotu '{item.item_type}'.",
        "character": await char_dict_with_equipment(char, db),
    }


@router.post("/unequip")
async def unequip_item(
    req: UnequipRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sundá item z daného slotu."""
    char = await _get_char(user, db)

    slot_attr = SLOT_MAP.get(req.slot)
    if not slot_attr:
        raise HTTPException(400, f"Neznámý slot '{req.slot}'.")

    if getattr(char, slot_attr) is None:
        raise HTTPException(400, "Slot je již prázdný.")

    item_id = getattr(char, slot_attr)
    setattr(char, slot_attr, None)

    await recalculate_with_gear(char, db)
    await db.commit()

    # Získej název
    item_res = await db.execute(select(Item).where(Item.id == item_id))
    item = item_res.scalar_one_or_none()

    return {
        "message": f"Item sundán ze slotu '{req.slot}'.",
        "character": await char_dict_with_equipment(char, db),
    }


@router.post("/sell")
async def sell_item(
    req: SellRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prodá item do shopu za sell_price."""
    char = await _get_char(user, db)

    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(
            InventoryItem.id == req.inv_item_id,
            InventoryItem.character_id == char.id,
        )
    )
    inv_item = inv_res.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    if req.quantity < 1 or req.quantity > inv_item.quantity:
        raise HTTPException(400, f"Neplatné množství. Máš {inv_item.quantity} ks.")

    # Zkontroluj že item není nasazen
    item_id = inv_item.item_id
    equipped_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    }
    if item_id in equipped_ids:
        raise HTTPException(400, "Nelze prodat nasazený item. Nejdřív ho sundej.")

    gold_earned = inv_item.item.sell_price * req.quantity
    char.gold += gold_earned

    if inv_item.quantity <= req.quantity:
        await db.delete(inv_item)
    else:
        inv_item.quantity -= req.quantity

    await db.commit()

    return {
        "message": f"Prodáno za {gold_earned} G.",
        "gold_earned": gold_earned,
        "gold_total": char.gold,
    }


@router.post("/use/{inv_item_id}")
async def use_item(
    inv_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Použije spotřební item (lektvar / svitek) — trvalé bonusy nebo XP."""
    char = await _get_char(user, db)

    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(
            InventoryItem.id == inv_item_id,
            InventoryItem.character_id == char.id,
        )
    )
    inv_item = inv_res.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item = inv_item.item
    if item.item_type != "potion":
        raise HTTPException(400, "Tento item nelze použít.")

    # Aplikuj trvalé stat bonusy
    stat_changes: dict[str, int] = {}
    bonuses = {
        "strength":     item.bonus_str,
        "dexterity":    item.bonus_dex,
        "intelligence": item.bonus_int,
        "endurance":    item.bonus_end,
        "luck":         item.bonus_luck,
    }
    for stat, val in bonuses.items():
        if val:
            setattr(char, stat, getattr(char, stat) + val)
            stat_changes[stat] = val

    # bonus_mp přechodně = XP bonus pro lektvary
    gained_xp = item.bonus_mp or 0
    if gained_xp:
        char.xp += gained_xp

    await recalculate_with_gear(char, db)

    # Level-up loop
    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        char.recalculate_stats()
        leveled_up.append(char.level)

    # Odeber 1 ks z inventáře
    if inv_item.quantity <= 1:
        await db.delete(inv_item)
    else:
        inv_item.quantity -= 1

    await db.commit()

    return {
        "message": f"'{item.name}' použit!",
        "stat_changes": stat_changes,
        "xp_gained": gained_xp,
        "leveled_up": leveled_up,
        "character": await char_dict_with_equipment(char, db),
    }
