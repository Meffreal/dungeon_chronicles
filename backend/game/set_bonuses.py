"""
game/set_bonuses.py — Combat efekty set bonusů pro CombatantConfig

Používá se v combat routerech (quest, arena, dungeon) pro získání
aktivních combat efektů set bonusů dané postavy.

Stat bonusy (HP, LUCK) jsou aplikovány dříve v recalculate_with_gear().
Tento modul vrací pouze COMBAT efekty předávané do CombatantConfig.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def get_char_set_combat_effects(char, db: AsyncSession) -> dict:
    """
    Vrátí dict aktivních combat efektů set bonusů pro danou postavu.
    Výsledek předat jako `set_bonuses=...` do CombatantConfig.

    Efekty:
      ability_dmg_pct   — bonus % dmg schopností (Bouřební Závoj 3pc)
      spell_echo_pct    — Spell Echo šance v % (Bouřební Závoj 5pc)
      first_strike      — bool, vždy útočit první (Přízračný Chodec 5pc)
      regen_every_round — bool, regenerace každé kolo souboje (Dračí Šupiny 5pc)

    Poznámka: Stat bonusy (HP +15%, LUCK +12%) jsou již zapečeny
    do char.hp_max a char.luck přes recalculate_with_gear() → není třeba
    předávat do CombatantConfig zvlášť.
    """
    from models.item import InventoryItem, Item
    from models.sets import get_active_set_bonuses

    eq_ids = [
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    ]

    equipped_items = []
    for item_id in eq_ids:
        if item_id is None:
            continue
        res = await db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.item))
            .where(
                InventoryItem.character_id == char.id,
                InventoryItem.item_id      == item_id,
            )
        )
        inv_item = res.scalar_one_or_none()
        if inv_item and inv_item.item:
            equipped_items.append(inv_item.item)
        else:
            # Fallback: plain Item (edge case)
            res2 = await db.execute(select(Item).where(Item.id == item_id))
            item = res2.scalar_one_or_none()
            if item:
                equipped_items.append(item)

    set_result = get_active_set_bonuses(equipped_items, char.cls)
    active     = set_result.get("active", {})

    effects: dict = {
        "ability_dmg_pct":   0,
        "spell_echo_pct":    0,
        "first_strike":      False,
        "regen_every_round": False,
    }

    for info in active.values():
        if info.get("ability_dmg_pct"):
            effects["ability_dmg_pct"] += info["ability_dmg_pct"]
        if info.get("spell_echo_pct"):
            effects["spell_echo_pct"] = max(
                effects["spell_echo_pct"], info["spell_echo_pct"]
            )
        if info.get("first_strike"):
            effects["first_strike"] = True
        if info.get("regen_every_round"):
            effects["regen_every_round"] = True

    return effects
