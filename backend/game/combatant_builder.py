"""
game/combatant_builder.py — Sestaví CombatantConfig z Character modelu.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from game.combat_engine import CombatantConfig
from game.combat_stats import CLASS_WEAPON_BASE


async def _get_gear_stats(
    char, db: AsyncSession
) -> tuple[int, int, int, int, int, int]:
    """Vrátí (weapon_dmg, armor_value, eq_str, eq_dex, eq_int, eq_luck) ze všech 7 slotů.

    Prochází weapon + 6 armor slotů jedním průchodem:
    - weapon_dmg: bonus_atk z weapon slotu (fallback na CLASS_WEAPON_BASE)
    - armor_value: součet bonus_def z armor slotů (weapon slot ignorován — záměrně)
    - eq_str/dex/int/luck: součet ze všech slotů
    """
    from models.item import Item

    weapon_dmg = CLASS_WEAPON_BASE.get(char.cls, 5)
    armor_val = eq_str = eq_dex = eq_int = eq_luck = 0

    slot_ids = [
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots,  char.eq_ring, char.eq_amulet,
    ]

    for idx, item_id in enumerate(slot_ids):
        if item_id is None:
            continue
        item = await db.get(Item, item_id)
        if not item:
            continue
        if idx == 0:  # weapon slot — bonus_atk jako weapon_dmg
            weapon_dmg = item.bonus_atk or CLASS_WEAPON_BASE.get(char.cls, 5)
        else:         # armor sloty — bonus_def jako armor
            armor_val += item.bonus_def or 0
        eq_str  += item.bonus_str  or 0
        eq_dex  += item.bonus_dex  or 0
        eq_int  += item.bonus_int  or 0
        eq_luck += item.bonus_luck or 0

    return weapon_dmg, armor_val, eq_str, eq_dex, eq_int, eq_luck


async def build_combatant_config(char, db: AsyncSession) -> CombatantConfig:
    """Sestaví CombatantConfig z Character ORM objektu."""
    from game.set_bonuses import get_char_set_combat_effects  # lazy import

    weapon_dmg, armor_value, eq_str, eq_dex, eq_int, eq_luck = await _get_gear_stats(char, db)

    s = char.strength     + eq_str
    d = char.dexterity    + eq_dex
    i = char.intelligence + eq_int

    cls = char.cls
    if cls == "warrior":
        primary, sec_a, sec_b = s, d, i
    elif cls == "ranger":
        primary, sec_a, sec_b = d, s, i
    elif cls == "mage":
        primary, sec_a, sec_b = i, s, d
    else:
        import logging
        logging.getLogger(__name__).warning(
            "build_combatant_config: neznámá třída '%s' pro char '%s' — primary_stat=0",
            char.cls, getattr(char, 'name', '?')
        )
        primary, sec_a, sec_b = 0, 0, 0

    set_bonuses = await get_char_set_combat_effects(char, db)
    talents     = char.get_talents() if hasattr(char, 'get_talents') else []

    return CombatantConfig(
        name         = char.name,
        hp           = char.hp_max,
        weapon_dmg   = weapon_dmg,
        armor_value  = armor_value,
        primary_stat = primary,
        secondary_a  = sec_a,
        secondary_b  = sec_b,
        luck         = char.luck + eq_luck,
        level        = char.level,
        cls          = char.cls,
        talents      = talents,
        talent_t2    = char.talent_t2_key or "",
        subclass     = char.subclass or "",
        set_bonuses  = set_bonuses,
    )
