"""
routers/inventory.py — Inventář, equip/unequip, prodej do shopu
"""
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character, xp_to_next, BUFF_DURATION_DAYS
from models.economy import log_gold, GoldReason
from models.item import (Item, InventoryItem, Rarity, RARITY_COLOR,
                         UPGRADE_COSTS, UPGRADE_STAT_MULT, UPGRADEABLE_RARITIES,
                         MAX_UPGRADE_LEVEL, UPGRADE_RARITY_CHAIN, UPGRADE_TIER_ICON)
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

class UseItemRequest(BaseModel):
    replace_buff: str | None = None  # název buffu, který chceme nahradit

# ── Helper ────────────────────────────────────────────────────────────────────
async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char

REPAIR_COST_PER_POINT = 3    # gold za každý bod durability
DURABILITY_LOSS_DUNGEON = 1  # ztráta durability po každém dungeon stagu
DURABILITY_LOSS_ARENA   = 2  # ztráta durability po arenové útoku


def _dur_mult(durability: int) -> float:
    """Vrátí multiplikátor stat bonusů dle durability (0–100)."""
    if durability >= 25:
        return 1.0
    if durability > 0:
        return 0.90
    return 0.80   # poškozeno — 20% penalizace


def _apply_equipment_bonuses(char: Character, inv_items: list):
    """Přičte přímé combat bonusy nasazených itemů ke stats postavy (s upgrade mult + durability).
    Přijímá InventoryItem objekty (preferovaně) nebo plain Item objekty (fallback).
    Primary stat bonusy (bonus_str atd.) se NE-ukládají do char — jsou zpracovány
    v recalculate_with_gear dočasně, aby nedocházelo k inflaci stats v DB.
    """
    for obj in inv_items:
        if obj is None:
            continue
        # Zjisti Item objekt, upgrade_level a durability
        if hasattr(obj, 'item'):      # InventoryItem
            item = obj.item
            ul   = getattr(obj, 'upgrade_level', 0) or 0
            dur  = getattr(obj, 'durability', 100)
            if dur is None:
                dur = 100
        else:                          # plain Item (fallback)
            item = obj
            ul   = 0
            dur  = 100
        if item is None:
            continue
        mult = UPGRADE_STAT_MULT[min(ul, MAX_UPGRADE_LEVEL)] * _dur_mult(dur)
        char.atk    += max(0, int(item.bonus_atk * mult)) if item.bonus_atk else 0
        char.def_   += max(0, int(item.bonus_def * mult)) if item.bonus_def else 0
        char.spd    += max(0, int(item.bonus_spd * mult)) if item.bonus_spd else 0
        char.hp_max += max(0, int(item.bonus_hp  * mult)) if item.bonus_hp  else 0
        char.mp_max += max(0, int(item.bonus_mp  * mult)) if item.bonus_mp  else 0

async def recalculate_with_gear(char: Character, db: AsyncSession):
    """Přepočítá stats postavy včetně všech nasazených itemů, set bonusů a upgrade levelů."""
    eq_ids = [
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    ]
    # Načti InventoryItem objekty (obsahují upgrade_level) místo plain Item
    equipped_inv_items: list[InventoryItem] = []
    for item_id in eq_ids:
        if item_id is not None:
            res = await db.execute(
                select(InventoryItem)
                .options(selectinload(InventoryItem.item))
                .where(InventoryItem.character_id == char.id,
                       InventoryItem.item_id == item_id)
            )
            inv_item = res.scalar_one_or_none()
            if inv_item and inv_item.item:
                equipped_inv_items.append(inv_item)
            else:
                # Fallback: plain Item (pro itemy bez záznamu v inventory — edge case)
                res2 = await db.execute(select(Item).where(Item.id == item_id))
                item = res2.scalar_one_or_none()
                if item:
                    equipped_inv_items.append(item)  # type: ignore[arg-type]

    equipped_items = [
        (ii.item if hasattr(ii, 'item') else ii) for ii in equipped_inv_items
    ]

    # Dočasně přidej primary stat bonusy z equipu
    eq_str  = sum(i.bonus_str  for i in equipped_items if i)
    eq_dex  = sum(i.bonus_dex  for i in equipped_items if i)
    eq_int  = sum(i.bonus_int  for i in equipped_items if i)
    eq_end  = sum(i.bonus_end  for i in equipped_items if i)
    eq_luck = sum(i.bonus_luck for i in equipped_items if i)

    char.strength     += eq_str
    char.dexterity    += eq_dex
    char.intelligence += eq_int
    char.endurance    += eq_end
    char.luck         += eq_luck

    char.recalculate_stats()

    char.strength     -= eq_str
    char.dexterity    -= eq_dex
    char.intelligence -= eq_int
    char.endurance    -= eq_end
    char.luck         -= eq_luck

    # Přidej přímé combat bonusy z equipu (s upgrade mult)
    _apply_equipment_bonuses(char, equipped_inv_items)

    # Aplikuj set bonusy — stat bonusy (HP, LUCK)
    from models.sets import get_active_set_bonuses
    set_result = get_active_set_bonuses(equipped_items, char.cls)
    hp_mult   = set_result["hp_multiplier"]
    luck_mult = set_result["luck_multiplier"]
    if hp_mult > 1.0:
        char.hp_max = int(char.hp_max * hp_mult)
    if luck_mult > 1.0:
        char.luck = int(char.luck * luck_mult)

async def _decrease_equipped_durability(char: Character, amount: int, db: AsyncSession):
    """Sníží durability všech nasazených itemů o `amount` (min 0)."""
    eq_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    } - {None}
    for item_id in eq_ids:
        res = await db.execute(
            select(InventoryItem).where(
                InventoryItem.character_id == char.id,
                InventoryItem.item_id      == item_id,
            )
        )
        inv_item = res.scalar_one_or_none()
        if inv_item:
            cur = inv_item.durability if inv_item.durability is not None else 100
            inv_item.durability = max(0, cur - amount)


def _repair_cost(inv_item: InventoryItem) -> int:
    """Vrátí cenu opravy jednoho itemu (0 pokud není poškozený)."""
    dur = inv_item.durability if inv_item.durability is not None else 100
    return max(0, (100 - dur) * REPAIR_COST_PER_POINT)


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
    await log_gold(db, char, gold_earned, GoldReason.INVENTORY_SELL,
                   {"item_id": item_id, "quantity": req.quantity, "sell_price": inv_item.item.sell_price})

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
    req: UseItemRequest | None = None,
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

    if req is None:
        req = UseItemRequest()

    # Stat bonusy → dočasný buff (ne permanentní změna)
    stat_changes: dict[str, int] = {}
    buff_duration_days: int | None = None
    has_stat_bonus = any([item.bonus_str, item.bonus_dex, item.bonus_int, item.bonus_end, item.bonus_luck])
    if has_stat_bonus:
        active_buffs = char.get_active_buffs()
        if len(active_buffs) >= 3:
            if req.replace_buff is None:
                raise HTTPException(409, detail={
                    "code": "MAX_BUFFS",
                    "msg": "Máš již 3 aktivní elixíry. Vyber který chceš nahradit.",
                    "buffs": active_buffs,
                })
            remaining = [b for b in active_buffs if b["name"] != req.replace_buff]
            if len(remaining) == len(active_buffs):
                raise HTTPException(400, "Zadaný elixír nebyl nalezen v aktivních buffech.")
            char.active_buffs_json = json.dumps(remaining)

        days       = BUFF_DURATION_DAYS.get(item.rarity, 1)
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)
        buff_duration_days = days
        char.add_buff(
            name      = item.name,
            expires_at= expires_at,
            bonus_str = item.bonus_str  or 0,
            bonus_dex = item.bonus_dex  or 0,
            bonus_int = item.bonus_int  or 0,
            bonus_end = item.bonus_end  or 0,
            bonus_luck= item.bonus_luck or 0,
        )
        if item.bonus_str:  stat_changes["strength"]     = item.bonus_str
        if item.bonus_dex:  stat_changes["dexterity"]    = item.bonus_dex
        if item.bonus_int:  stat_changes["intelligence"] = item.bonus_int
        if item.bonus_end:  stat_changes["endurance"]    = item.bonus_end
        if item.bonus_luck: stat_changes["luck"]         = item.bonus_luck

    # bonus_mp = okamžitý XP (scrolly zkušeností)
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
        leveled_up.append(char.level)
    if leveled_up:
        await recalculate_with_gear(char, db)

    # Odeber 1 ks z inventáře
    if inv_item.quantity <= 1:
        await db.delete(inv_item)
    else:
        inv_item.quantity -= 1

    await db.commit()

    return {
        "message": f"'{item.name}' použit!",
        "stat_changes": stat_changes,
        "buff_duration_days": buff_duration_days,
        "xp_gained": gained_xp,
        "leveled_up": leveled_up,
        "character": await char_dict_with_equipment(char, db),
    }


@router.post("/upgrade/{inv_item_id}")
async def upgrade_item(
    inv_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vylepší výbavový item o jednu úroveň rarity (Common→Uncommon→Rare→Epic).
    Cena: 500G / 2 000G / 8 000G. Max. 3 upgrady na item.
    Funguje pouze na vybavení (ne lektvary). Epic, Legendary a Set nemohou být upgradovány.
    """
    char = await _get_char(user, db)

    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.id == inv_item_id,
               InventoryItem.character_id == char.id)
    )
    inv_item = inv_res.scalar_one_or_none()
    if not inv_item or not inv_item.item:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    item = inv_item.item
    ul   = inv_item.upgrade_level or 0

    if item.item_type == "potion":
        raise HTTPException(400, "Lektvary nelze vylepšovat.")

    if item.rarity not in UPGRADEABLE_RARITIES:
        raise HTTPException(400, f"Rarity '{item.rarity}' nelze dále vylepšit.")

    if ul >= MAX_UPGRADE_LEVEL:
        raise HTTPException(400, "Item je již na maximální úrovni vylepšení (★★★).")

    cost = UPGRADE_COSTS[ul]
    if char.gold < cost:
        raise HTTPException(400, f"Nedostatek gold. Potřebuješ {cost} G, máš {char.gold} G.")

    char.gold -= cost
    await log_gold(db, char, -cost, GoldReason.INVENTORY_SELL,
                   {"item_id": item.id, "upgrade_from": ul, "upgrade_to": ul + 1,
                    "reason": "item_upgrade"})
    inv_item.upgrade_level = ul + 1

    await recalculate_with_gear(char, db)
    await db.commit()

    new_ul     = inv_item.upgrade_level
    base_idx   = UPGRADE_RARITY_CHAIN.index(item.rarity) if item.rarity in UPGRADE_RARITY_CHAIN else 0
    new_rarity = UPGRADE_RARITY_CHAIN[min(base_idx + new_ul, len(UPGRADE_RARITY_CHAIN) - 1)]
    return {
        "message": (f"✦ '{item.name}' vylepšen na {UPGRADE_TIER_ICON[new_ul]}! "
                    f"Nová rarity: {new_rarity}. Utraceno: {cost} G."),
        "upgrade_level": new_ul,
        "new_rarity": new_rarity,
        "cost": cost,
        "character": await char_dict_with_equipment(char, db),
        "inv_item": inv_item.to_dict(),
    }


# ── Durability — Repair ───────────────────────────────────────────────────────

@router.post("/repair")
async def repair_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opraví všechny nasazené itemy. Strhne gold dle durability ztráty."""
    char = await _get_char(user, db)

    eq_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots, char.eq_ring, char.eq_amulet,
    } - {None}

    total_cost = 0
    repaired = []
    for item_id in eq_ids:
        res = await db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.item))
            .where(InventoryItem.character_id == char.id, InventoryItem.item_id == item_id)
        )
        inv_item = res.scalar_one_or_none()
        if inv_item:
            cost = _repair_cost(inv_item)
            if cost > 0:
                total_cost += cost
                repaired.append({"name": inv_item.item.name if inv_item.item else "?", "cost": cost})

    if total_cost == 0:
        raise HTTPException(400, "Všechny nasazené itemy jsou v perfektním stavu.")

    if char.gold < total_cost:
        raise HTTPException(400, f"Nedostatek gold. Oprava stojí {total_cost} G, máš {char.gold} G.")

    # Proveď opravu
    char.gold -= total_cost
    await log_gold(db, char, -total_cost, GoldReason.INVENTORY_SELL,
                   {"reason": "repair_all", "count": len(repaired)})

    for item_id in eq_ids:
        res = await db.execute(
            select(InventoryItem).where(
                InventoryItem.character_id == char.id, InventoryItem.item_id == item_id
            )
        )
        inv_item = res.scalar_one_or_none()
        if inv_item:
            inv_item.durability = 100

    await recalculate_with_gear(char, db)
    await db.commit()

    return {
        "message":    f"Vybavení opraveno za {total_cost} G.",
        "total_cost": total_cost,
        "repaired":   repaired,
        "character":  await char_dict_with_equipment(char, db),
    }


@router.post("/repair/{inv_item_id}")
async def repair_item(
    inv_item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Opraví jeden konkrétní item z inventáře."""
    char = await _get_char(user, db)

    res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.id == inv_item_id, InventoryItem.character_id == char.id)
    )
    inv_item = res.scalar_one_or_none()
    if not inv_item:
        raise HTTPException(404, "Item nenalezen v inventáři.")

    cost = _repair_cost(inv_item)
    if cost == 0:
        raise HTTPException(400, "Item je již v perfektním stavu.")

    if char.gold < cost:
        raise HTTPException(400, f"Nedostatek gold. Oprava stojí {cost} G, máš {char.gold} G.")

    char.gold        -= cost
    inv_item.durability = 100
    await log_gold(db, char, -cost, GoldReason.INVENTORY_SELL,
                   {"reason": "repair_item", "inv_item_id": inv_item_id})

    await recalculate_with_gear(char, db)
    await db.commit()

    item_name = inv_item.item.name if inv_item.item else "?"
    return {
        "message":   f"'{item_name}' opraveno za {cost} G.",
        "cost":      cost,
        "character": await char_dict_with_equipment(char, db),
    }
