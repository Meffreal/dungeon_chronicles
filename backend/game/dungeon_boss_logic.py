"""
game/dungeon_boss_logic.py — Pure logic for the 50-boss dungeon system.

No HTTP, no DB access — takes pre-loaded data and returns computed results.
"""
from __future__ import annotations
from datetime import datetime, timedelta

from game.dungeon_boss_data import (
    DUNGEON_BOSS_DEFINITIONS,
    DUNGEON_ONLY_ITEMS,
    DUNGEON_UNLOCK_CONDITIONS,
    boss_enemy_mult,
)
from game.combat_engine import CombatantConfig

BOSS_COOLDOWN_HOURS = 1
TOTAL_BOSSES = 50


def get_boss_def(dungeon_key: str, boss_num: int) -> dict | None:
    """Return boss definition dict for a given dungeon and boss number."""
    bosses = DUNGEON_BOSS_DEFINITIONS.get(dungeon_key, [])
    return next((b for b in bosses if b["num"] == boss_num), None)


def is_milestone_boss(boss_num: int) -> bool:
    """Returns True if this boss guarantees an item drop."""
    return boss_num % 5 == 0


def get_item_tier(boss_num: int) -> int:
    """
    Returns item tier index (0-4) for a milestone boss.
    Bosses 5,10 -> 0 | 15,20 -> 1 | 25,30 -> 2 | 35,40 -> 3 | 45,50 -> 4
    """
    return (boss_num // 5 - 1) // 2


def get_milestone_item(dungeon_key: str, cls: str, boss_num: int) -> tuple | None:
    """
    Returns the item tuple for a milestone boss drop.
    Returns None if not a milestone, or if dungeon/class not found.
    """
    if not is_milestone_boss(boss_num):
        return None
    dungeon_items = DUNGEON_ONLY_ITEMS.get(dungeon_key, {})
    class_items = dungeon_items.get(cls, [])
    tier = get_item_tier(boss_num)
    if tier < len(class_items):
        return class_items[tier]
    return None


def build_boss_enemy(
    dungeon_key: str,
    boss_num: int,
    char_level: int,
) -> CombatantConfig:
    """
    Builds a CombatantConfig for the given boss.
    """
    boss = get_boss_def(dungeon_key, boss_num)
    if not boss:
        raise ValueError(f"Boss {boss_num} not found in {dungeon_key}")

    min_level = DUNGEON_UNLOCK_CONDITIONS.get(dungeon_key, {}).get("min_level", 1)
    base_lvl = max(char_level, min_level)
    mult = boss_enemy_mult(boss_num)

    is_boss = boss_num % 5 == 0

    hp   = int(60 * base_lvl * mult)
    atk  = int(9  * base_lvl * mult)
    def_ = int(5  * base_lvl * mult)
    spd  = int(7  * base_lvl * mult * 0.8)

    return CombatantConfig(
        name=boss["name"],
        hp=hp,
        weapon_dmg=atk,
        armor_value=def_,
        primary_stat=0,
        secondary_a=0,
        secondary_b=0,
        luck=int(3 * mult),
        level=base_lvl,
        cls="",
        is_boss=is_boss,
        phases=[],
        special_abilities=[],
        modifier_statuses=[],
    )


def calc_boss_rewards(dungeon_key: str, boss_num: int, char_level: int) -> dict:
    """
    Calculates XP and Gold reward for defeating a boss.
    """
    mult = boss_enemy_mult(boss_num)
    xp   = int(50 * char_level * mult)
    gold = int(25 * char_level * mult)
    return {"xp": xp, "gold": gold}


def check_dungeon_unlocked(
    dungeon_key: str,
    char_level: int,
    progress_map: dict[str, int],
    completed_chain_ids: list[int],
) -> tuple[bool, str]:
    """
    Checks whether a character may enter a dungeon.
    Returns (is_unlocked: bool, reason: str)
    """
    cond = DUNGEON_UNLOCK_CONDITIONS.get(dungeon_key)
    if not cond:
        return False, "Unknown dungeon."

    if char_level < cond["min_level"]:
        return False, f"Requires level {cond['min_level']}."

    prev = cond.get("prev_dungeon")
    if prev:
        required_bosses = cond["min_bosses_in_prev"]
        defeated_in_prev = progress_map.get(prev, 0)
        if defeated_in_prev < required_bosses:
            return False, (
                f"Defeat {required_bosses} bosses in the previous dungeon first "
                f"({defeated_in_prev}/{required_bosses})."
            )

    chain_id = cond.get("attunement_chain_id")
    if chain_id is not None and chain_id not in completed_chain_ids:
        return False, "Complete the attunement quest chain first."

    return True, ""


def boss_cooldown_until(now: datetime) -> datetime:
    """Returns the cooldown_until datetime after a boss fight."""
    return now + timedelta(hours=BOSS_COOLDOWN_HOURS)
