"""
game/sim_builds.py — Benchmark builds odvozené z reálných herních dat.

Automaticky načítá SEED_ITEMS a SEED_CLASS_ITEMS ze seed.py a sestavuje
"nejlépe dostupné vybavení" pro každou třídu na daném levelu.

Změny v seed.py (nové itemy, upravené stats) se automaticky projeví v sim.

Použití:
    from game.sim_builds import get_benchmark_build, get_best_gear
    build = get_benchmark_build("warrior", level=30)
    gear  = get_best_gear("mage", max_level=30, max_rarity="epic")
"""

from game.combat_stats import CLASS_HP_MULT

# ── Indexy tuple formátu SEED_ITEMS / SEED_CLASS_ITEMS ────────────────────────
# (name, type, rarity, desc, icon, atk, def_, spd, hp, xp,
#  s_str, s_dex, s_int, s_end, s_luck, min_level, sell, hint_class)
_I_TYPE     = 1
_I_RARITY   = 2
_I_ATK      = 5
_I_DEF      = 6
_I_STR      = 10
_I_DEX      = 11
_I_INT      = 12
_I_END      = 13
_I_LUCK     = 14
_I_MIN_LVL  = 15
_I_HINT_CLS = 17

RARITY_ORDER: dict[str, int] = {
    "common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4, "set": 5,
}
EQUIPMENT_SLOTS = ["weapon", "armor", "helmet", "gloves", "boots", "ring", "amulet"]

# Primary stat index per class (pro výběr "nejlepší zbroje" — max def + 0.5×primary)
_PRIMARY_STAT_IDX: dict[str, int] = {
    "warrior": _I_STR,
    "mage":    _I_INT,
    "ranger":  _I_DEX,
}

# ── Základní přidělení stat bodů na level 30 (bez equipu) ────────────────────
# Reprezentuje ~30 bodů z level-up (1/úroveň): 60% primary, 25% secondary_a, 15% secondary_b
# Zbytek do secondary_b/luck. Odráží typického focused buildě.
BASE_STAT_ALLOCS: dict[str, dict[str, int]] = {
    "warrior": {"primary": 18, "secondary_a": 8,  "secondary_b": 4, "luck": 5},
    "mage":    {"primary": 18, "secondary_a": 6,  "secondary_b": 6, "luck": 5},
    "ranger":  {"primary": 18, "secondary_a": 8,  "secondary_b": 4, "luck": 5},
}


def get_best_gear(cls: str, max_level: int = 30, max_rarity: str = "legendary") -> dict:
    """
    Najde nejlepší equipment pro třídu na daném levelu z herních dat.

    Výběr per slot:
    - weapon  → maximalizuje bonus_atk
    - ostatní → maximalizuje bonus_def + 0.5 × primary_stat třídy

    Args:
        cls:         Třída ("warrior" / "mage" / "ranger")
        max_level:   Maximální min_level itemu (default 30)
        max_rarity:  Nejvyšší dovolená rarита (default "legendary")

    Returns:
        dict: weapon_dmg, armor_value, bonus_str/dex/int/end/luck
              + selected_items {slot: item_name} pro debug
    """
    from game.seed import SEED_ITEMS, SEED_CLASS_ITEMS

    max_rarity_val = RARITY_ORDER.get(max_rarity, 4)

    eligible = [
        r for r in SEED_ITEMS + SEED_CLASS_ITEMS
        if r[_I_TYPE] != "potion"
        and r[_I_MIN_LVL] <= max_level
        and RARITY_ORDER.get(r[_I_RARITY], 0) <= max_rarity_val
        and (r[_I_HINT_CLS] is None or r[_I_HINT_CLS] == cls)
    ]

    pk_idx = _PRIMARY_STAT_IDX.get(cls, _I_STR)

    totals: dict = {
        "weapon_dmg": 0, "armor_value": 0,
        "bonus_str": 0, "bonus_dex": 0, "bonus_int": 0,
        "bonus_end": 0, "bonus_luck": 0,
        "selected_items": {},
    }

    for slot in EQUIPMENT_SLOTS:
        candidates = [r for r in eligible if r[_I_TYPE] == slot]
        if not candidates:
            continue

        if slot == "weapon":
            best = max(candidates, key=lambda r: r[_I_ATK])
        else:
            best = max(candidates, key=lambda r: r[_I_DEF] + r[pk_idx] * 0.5)

        totals["weapon_dmg"]  += best[_I_ATK]
        totals["armor_value"] += best[_I_DEF]
        totals["bonus_str"]   += best[_I_STR]
        totals["bonus_dex"]   += best[_I_DEX]
        totals["bonus_int"]   += best[_I_INT]
        totals["bonus_end"]   += best[_I_END]
        totals["bonus_luck"]  += best[_I_LUCK]
        totals["selected_items"][slot] = f"{best[0]} ({best[_I_RARITY]})"

    return totals


def get_benchmark_build(cls: str, level: int = 30,
                        max_rarity: str = "legendary") -> dict:
    """
    Sestaví kompletní build dict pro danou třídu a level.
    weapon_dmg, armor_value a stat bonusy jsou odvozeny z reálných herních dat.

    Returns:
        dict: cls, weapon_dmg, armor_value, primary_stat, secondary_a,
              secondary_b, luck, gear (selected_items pro debug)
    """
    gear = get_best_gear(cls, max_level=level, max_rarity=max_rarity)
    base = BASE_STAT_ALLOCS.get(cls, BASE_STAT_ALLOCS["warrior"])

    if cls == "warrior":
        primary_stat = base["primary"]      + gear["bonus_str"]
        secondary_a  = base["secondary_a"]  + gear["bonus_dex"]
        secondary_b  = base["secondary_b"]  + gear["bonus_int"]
    elif cls == "ranger":
        primary_stat = base["primary"]      + gear["bonus_dex"]
        secondary_a  = base["secondary_a"]  + gear["bonus_str"]
        secondary_b  = base["secondary_b"]  + gear["bonus_int"]
    elif cls == "mage":
        primary_stat = base["primary"]      + gear["bonus_int"]
        secondary_a  = base["secondary_a"]  + gear["bonus_str"]
        secondary_b  = base["secondary_b"]  + gear["bonus_dex"]
    else:
        primary_stat = base["primary"]      + gear["bonus_str"]
        secondary_a  = base["secondary_a"]  + gear["bonus_dex"]
        secondary_b  = base["secondary_b"]  + gear["bonus_int"]

    return {
        "cls":          cls,
        "weapon_dmg":   gear["weapon_dmg"],
        "armor_value":  gear["armor_value"],
        "primary_stat": primary_stat,
        "secondary_a":  secondary_a,
        "secondary_b":  secondary_b,
        "luck":         base["luck"] + gear["bonus_luck"],
        "gear":         gear["selected_items"],
    }
