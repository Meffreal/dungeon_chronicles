"""
game/combat_stats.py — Pomocné funkce pro výpočet combat statistik.

Odděleno od combat_engine.py aby bylo testovatelné a importovatelné
z routerů bez tažení celého enginu.
"""

# Třídně-specifické konstanty
CLASS_WEAPON_BASE: dict[str, int] = {
    "warrior": 8,
    "ranger":  6,
    "mage":    4,
}

CLASS_ARMOR_CAPS: dict[str, float] = {
    "warrior": 0.45,
    "ranger":  0.25,
    "mage":    0.15,
}

CLASS_HP_MULT: dict[str, int] = {
    "warrior": 4,
    "ranger":  3,
    "mage":    2,
}


def soft_cap_stat(value: int) -> float:
    """Aplikuje soft cap na primární stat před damage výpočtem.
    0-50: 100% | 51-150: 70% | 151+: 30%
    """
    if value <= 50:
        return float(value)
    elif value <= 150:
        return 50.0 + (value - 50) * 0.70
    else:
        return 50.0 + 70.0 + (value - 150) * 0.30


def calc_damage_components(
    cls: str,
    str_: int, dex: int, int_: int,
    weapon_dmg: int,
) -> tuple[float, float, float]:
    """Vypočítá (total_base_damage, sec_a_contrib, sec_b_contrib) pro třídu.

    Warrior:  weapon × (1 + STR/10) + DEX/2 + INT/2
    Ranger:   weapon × (1 + DEX/10) + STR/2 + INT/2
    Mage:     weapon × (1 + INT/10) + STR/2 + DEX/2
    """
    if cls == "warrior":
        primary = soft_cap_stat(str_)
        sec_a   = soft_cap_stat(dex) / 2
        sec_b   = soft_cap_stat(int_) / 2
    elif cls == "ranger":
        primary = soft_cap_stat(dex)
        sec_a   = soft_cap_stat(str_) / 2
        sec_b   = soft_cap_stat(int_) / 2
    elif cls == "mage":
        primary = soft_cap_stat(int_)
        sec_a   = soft_cap_stat(str_) / 2
        sec_b   = soft_cap_stat(dex) / 2
    else:
        # AI/boss — používá weapon_dmg jako flat damage, žádný primary stat bonus
        primary = 0.0
        sec_a   = 0.0
        sec_b   = 0.0

    base = weapon_dmg * (1 + primary / 10) + sec_a + sec_b
    return base, sec_a, sec_b


def calc_armor_pct(cls: str, armor_value: int, enemy_level: int) -> float:
    """Vrátí damage reduction % pro dané brnění a level nepřítele.

    Formula: armor_value / (enemy_level * 100), cappováno třídním limitem.
    Příklad: armor=90, level=10 → 90/(10*100) = 0.09
    """
    eff_level = max(1, enemy_level)
    cap = CLASS_ARMOR_CAPS.get(cls, 0.25)
    return min(cap, armor_value / (eff_level * 100))


def calc_crit_chance(luck: int, enemy_level: int) -> float:
    """Šance na krit: LCK / (enemy_level × 4), max 50%.

    Příklad: luck=10, enemy_level=10 → 10/(10*4) = 0.25
    """
    eff_level = max(1, enemy_level)
    return min(0.50, luck / (eff_level * 4))


def calc_hp(cls: str, endurance: int, level: int) -> int:
    """HP: END × class_mult × (level + 1), min 10."""
    mult = CLASS_HP_MULT.get(cls, 4)
    return max(10, endurance * mult * (level + 1))
