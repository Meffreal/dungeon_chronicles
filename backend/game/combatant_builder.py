"""
game/combatant_builder.py — Sestaví CombatantConfig z Character modelu.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from game.combat_engine import CombatantConfig
from game.combat_stats import CLASS_WEAPON_BASE


async def _get_weapon_dmg(char, db: AsyncSession) -> int:
    """Vrátí weapon_dmg z vybavené zbraně nebo class base."""
    if char.eq_weapon:
        from models.item import Item
        weapon = await db.get(Item, char.eq_weapon)
        if weapon:
            return weapon.bonus_atk or CLASS_WEAPON_BASE.get(char.cls, 5)
    return CLASS_WEAPON_BASE.get(char.cls, 5)


async def _get_armor_value(char, db: AsyncSession) -> int:
    """Součet bonus_def ze všech vybavených předmětů."""
    total = 0
    slot_ids = [
        char.eq_helmet, char.eq_armor, char.eq_gloves,
        char.eq_boots, char.eq_ring, char.eq_amulet,
    ]
    from models.item import Item
    for item_id in slot_ids:
        if item_id:
            item = await db.get(Item, item_id)
            if item:
                total += item.bonus_def or 0
    return total


def _primary_secondary(char) -> tuple[int, int, int]:
    """Vrátí (primary_stat, secondary_a, secondary_b) dle třídy."""
    cls = char.cls
    s, d, i = char.strength, char.dexterity, char.intelligence
    if cls == "warrior":
        return s, d, i
    elif cls == "ranger":
        return d, s, i
    elif cls == "mage":
        return i, s, d
    else:
        return 0, 0, 0


async def build_combatant_config(char, db: AsyncSession) -> CombatantConfig:
    """Sestaví CombatantConfig z Character ORM objektu."""
    from game.set_bonuses import get_char_set_combat_effects  # lazy import
    weapon_dmg   = await _get_weapon_dmg(char, db)
    armor_value  = await _get_armor_value(char, db)
    primary, sec_a, sec_b = _primary_secondary(char)
    set_bonuses  = await get_char_set_combat_effects(char, db)
    talents      = char.get_talents() if hasattr(char, 'get_talents') else []

    return CombatantConfig(
        name         = char.name,
        hp           = char.hp_max,
        weapon_dmg   = weapon_dmg,
        armor_value  = armor_value,
        primary_stat = primary,
        secondary_a  = sec_a,
        secondary_b  = sec_b,
        luck         = char.luck,
        level        = char.level,
        cls          = char.cls,
        talents      = talents,
        talent_t2    = char.talent_t2_key or "",
        subclass     = char.subclass or "",
        set_bonuses  = set_bonuses,
    )
