"""
game/bloodline.py — Bloodline meta-progression logika

Bloodline je per-user systém. Každá smrt postavy přidá XP do Bloodline.
XP se nikdy neresetuje — kumulují se přes všechny runy.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ── Bloodline leveling ─────────────────────────────────────────────────────
# XP potřebné pro každý level (kumulativní threshold)
BLOODLINE_XP_THRESHOLDS = [
    0,     # level 0 → 1:   start
    100,   # level 1 → 2
    250,   # level 2 → 3
    500,   # level 3 → 4
    900,   # level 4 → 5
    1400,  # level 5 → 6
    2100,  # level 6 → 7
    3000,  # level 7 → 8
    4200,  # level 8 → 9
    5700,  # level 9 → 10
    7500,  # level 10 → 11
    9800,  # level 11 → 12
    12600, # level 12 → 13
    16000, # level 13 → 14
    20000, # level 14 → 15
    25000, # level 15 → 16
    31000, # level 16 → 17
    38000, # level 17 → 18
    46000, # level 18 → 19
    55000, # level 19 → 20
    65000, # level 20 → 21
]

def xp_to_bloodline_level(total_xp: int) -> int:
    """Vrátí bloodline level pro dané total_xp."""
    level = 0
    for threshold in BLOODLINE_XP_THRESHOLDS:
        if total_xp >= threshold:
            level += 1
        else:
            break
    return max(0, level - 1)

def bloodline_xp_progress(total_xp: int) -> dict:
    """Vrátí current level, XP v aktuálním levelu, XP potřebné do dalšího."""
    level = xp_to_bloodline_level(total_xp)
    current_threshold = BLOODLINE_XP_THRESHOLDS[level] if level < len(BLOODLINE_XP_THRESHOLDS) else BLOODLINE_XP_THRESHOLDS[-1]
    next_threshold = BLOODLINE_XP_THRESHOLDS[level + 1] if level + 1 < len(BLOODLINE_XP_THRESHOLDS) else None
    xp_in_level = total_xp - current_threshold
    xp_needed = (next_threshold - current_threshold) if next_threshold else None
    return {
        "level": level,
        "xp_in_level": xp_in_level,
        "xp_needed": xp_needed,
        "total_xp": total_xp,
        "is_max_level": next_threshold is None,
    }

# ── XP Formula ─────────────────────────────────────────────────────────────
def calculate_death_bloodline_xp(char_level: int, days_survived: int, dungeons_cleared: int) -> int:
    """
    Formula: bloodline_xp = char.level * 10 + days_survived * 5 + dungeons_cleared * 3
    Minimum 10 XP (i krátký run přispěje).
    """
    xp = char_level * 10 + days_survived * 5 + dungeons_cleared * 3
    return max(10, xp)

# ── Unlock tabulka ─────────────────────────────────────────────────────────
# Každý unlock: {"type": str, "value": varies, "description": str}
BLOODLINE_UNLOCKS: dict[int, list[dict]] = {
    1: [
        {"type": "stat_bonus", "stat": "hp_flat", "value": 10,
         "description": "+10 HP pro nové hrdiny (krev pamatuje odolnost)"},
    ],
    2: [
        {"type": "gold_bonus", "value": 50,
         "description": "+50 zlata na startu (rodinné dědictví)"},
    ],
    3: [
        {"type": "stat_bonus", "stat": "atk_pct", "value": 0.02,
         "description": "+2% útok (předkova bojová paměť)"},
    ],
    4: [
        {"type": "stat_bonus", "stat": "def_pct", "value": 0.02,
         "description": "+2% obrana"},
    ],
    5: [
        {"type": "stat_bonus", "stat": "hp_flat", "value": 15,
         "description": "+15 HP (krevní linie se kalí)"},
        {"type": "cosmetic", "value": "portrait_frame_bloodline_1",
         "description": "Odemčen: portrétní rám 'Krevní Linie'"},
    ],
    6: [
        {"type": "subclass_unlock_early", "value": -5,
         "description": "Subclass odemčena o 5 levelů dříve (level 15 místo 20)"},
    ],
    7: [
        {"type": "stat_bonus", "stat": "spd_flat", "value": 3,
         "description": "+3 rychlost (reflexy předků)"},
    ],
    8: [
        {"type": "gold_bonus", "value": 100,
         "description": "+100 zlata na startu"},
    ],
    9: [
        {"type": "stat_bonus", "stat": "luck_flat", "value": 2,
         "description": "+2 luck (štěstí se dědí)"},
    ],
    10: [
        {"type": "subclass_unlock_early", "value": -10,
         "description": "Subclass odemčena o 10 levelů dříve (level 10 místo 20)"},
        {"type": "cosmetic", "value": "portrait_frame_bloodline_2",
         "description": "Odemčen: portrétní rám 'Dávná Krev'"},
        {"type": "title", "value": "Dávná Krev",
         "description": "Titul: 'Dávná Krev'"},
    ],
    11: [
        {"type": "stat_bonus", "stat": "hp_pct", "value": 0.05,
         "description": "+5% max HP (krev předků teče v žilách)"},
    ],
    12: [
        {"type": "cosmetic", "value": "portrait_frame_bloodline_3",
         "description": "Odemčen: portrétní rám 'Věčná Linie'"},
    ],
    15: [
        {"type": "stat_bonus", "stat": "atk_pct", "value": 0.05,
         "description": "+5% útok"},
        {"type": "title", "value": "Věčná Krev",
         "description": "Titul: 'Věčná Krev'"},
    ],
    20: [
        {"type": "cosmetic", "value": "portrait_frame_bloodline_4",
         "description": "Odemčen: portrétní rám 'Nesmrtelná Linie'"},
        {"type": "title", "value": "Nesmrtelná Krev",
         "description": "Titul: 'Nesmrtelná Krev'"},
    ],
}

def get_unlocks_for_level(level: int) -> list[dict]:
    """Vrátí všechny unlocky pro daný bloodline level (včetně nižších)."""
    result = []
    for lvl in range(1, level + 1):
        result.extend(BLOODLINE_UNLOCKS.get(lvl, []))
    return result

def get_new_unlocks_at_level(level: int) -> list[dict]:
    """Vrátí pouze nové unlocky při dosažení konkrétního levelu."""
    return BLOODLINE_UNLOCKS.get(level, [])

# ── Ancestor Memories (level 21+) ──────────────────────────────────────────
def generate_ancestor_memories(fallen_heroes: list[dict]) -> list[dict]:
    """
    Generuje Ancestor Memories z historie padlých hrdinů.

    fallen_heroes: list of dicts s klíči:
      - name, cls, level, days_survived, killed_by, death_dungeon

    Vrátí list memory dicts: {"description": str, "bonus_type": str, "bonus_value": varies}
    """
    memories = []

    if not fallen_heroes:
        return memories

    # "Předek byl Mage" → +3% spell/mp bonus
    mages = [h for h in fallen_heroes if h.get("cls") == "mage"]
    if len(mages) >= 3:
        memories.append({
            "description": f"Krev mágů teče v žilách — {len(mages)} předků ovládalo magii",
            "bonus_type": "stat_bonus",
            "stat": "mp_flat",
            "value": len(mages) * 2,
        })

    # "Předek přežil 30+ dní" → +5 max HP
    long_survivors = [h for h in fallen_heroes if h.get("days_survived", 0) >= 30]
    if long_survivors:
        memories.append({
            "description": f"{len(long_survivors)} předků přežilo déle než měsíc — jejich odolnost žije dál",
            "bonus_type": "stat_bonus",
            "stat": "hp_flat",
            "value": len(long_survivors) * 5,
        })

    # Nejvyšší dosažený level
    max_level = max((h.get("level", 0) for h in fallen_heroes), default=0)
    if max_level >= 30:
        memories.append({
            "description": f"Nejsilnější předek dosáhl levelu {max_level} — jeho síla rezonuje",
            "bonus_type": "stat_bonus",
            "stat": "atk_pct",
            "value": 0.03,
        })

    # Válečníci v rodině
    warriors = [h for h in fallen_heroes if h.get("cls") == "warrior"]
    if len(warriors) >= 5:
        memories.append({
            "description": f"Rodina válečníků — {len(warriors)} předků neslo meč",
            "bonus_type": "stat_bonus",
            "stat": "def_pct",
            "value": 0.03,
        })

    return memories

# ── DB helpers ─────────────────────────────────────────────────────────────
async def get_or_create_bloodline(user_id: int, db: "AsyncSession"):
    """Vrátí existující Bloodline nebo vytvoří novou pro uživatele."""
    from sqlalchemy import select
    from models.bloodline import Bloodline

    result = await db.execute(select(Bloodline).where(Bloodline.user_id == user_id))
    bloodline = result.scalar_one_or_none()

    if not bloodline:
        bloodline = Bloodline(user_id=user_id, total_xp=0, level=0, unlocks_json={})
        db.add(bloodline)
        await db.flush()

    return bloodline

async def award_death_bloodline_xp(
    user_id: int,
    char_level: int,
    days_survived: int,
    dungeons_cleared: int,
    db: "AsyncSession",
) -> dict:
    """
    Přičte Bloodline XP při permadeath. Vrátí dict s výsledkem.
    Volat z dungeon permadeath handleru.
    """
    bloodline = await get_or_create_bloodline(user_id, db)

    xp_gained = calculate_death_bloodline_xp(char_level, days_survived, dungeons_cleared)
    old_level = bloodline.level

    bloodline.total_xp += xp_gained
    bloodline.level = xp_to_bloodline_level(bloodline.total_xp)

    new_level = bloodline.level
    new_unlocks = []
    for lvl in range(old_level + 1, new_level + 1):
        new_unlocks.extend(get_new_unlocks_at_level(lvl))

    # Aktualizuj unlocks_json
    all_unlocks = get_unlocks_for_level(new_level)
    bloodline.unlocks_json = {
        "unlocks": all_unlocks,
        "last_updated": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }

    return {
        "xp_gained": xp_gained,
        "total_xp": bloodline.total_xp,
        "old_level": old_level,
        "new_level": new_level,
        "level_ups": new_level - old_level,
        "new_unlocks": new_unlocks,
    }
