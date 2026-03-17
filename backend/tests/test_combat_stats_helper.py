import pytest
from game.combat_stats import (
    calc_damage_components,
    CLASS_WEAPON_BASE,
    CLASS_ARMOR_CAPS,
    calc_armor_pct,
)

def test_warrior_damage_components():
    dmg, sec_a, sec_b = calc_damage_components("warrior", str_=30, dex=10, int_=5, weapon_dmg=20)
    # base = 20*(1+30/10) + 10/2 + 5/2 = 80 + 5 + 2 = 87
    assert dmg == pytest.approx(87, abs=1)

def test_mage_damage_components():
    dmg, sec_a, sec_b = calc_damage_components("mage", str_=5, dex=8, int_=30, weapon_dmg=20)
    # base = 20*(1+30/10) + 5/2 + 8/2 = 80 + 2 + 4 = 86
    assert dmg == pytest.approx(86, abs=1)

def test_ranger_damage_components():
    dmg, sec_a, sec_b = calc_damage_components("ranger", str_=9, dex=30, int_=8, weapon_dmg=20)
    # base = 20*(1+30/10) + 9/2 + 8/2 = 80 + 4 + 4 = 88
    assert dmg == pytest.approx(88, abs=1)

def test_warrior_base_weapon_if_unarmed():
    base = CLASS_WEAPON_BASE["warrior"]
    assert base == 8

def test_armor_cap_warrior():
    assert CLASS_ARMOR_CAPS["warrior"] == 0.35

def test_armor_cap_mage():
    assert CLASS_ARMOR_CAPS["mage"] == 0.20

def test_armor_pct_divides_by_enemy_level():
    from game.combat_stats import calc_armor_pct
    pct = calc_armor_pct("warrior", armor_value=90, enemy_level=10)
    assert pct == pytest.approx(0.09)

def test_armor_pct_capped():
    pct = calc_armor_pct("warrior", armor_value=9000, enemy_level=1)
    assert pct == pytest.approx(0.35)

def test_armor_pct_no_division_by_zero():
    pct = calc_armor_pct("mage", armor_value=50, enemy_level=0)
    assert pct <= 0.20

def test_crit_chance_new():
    from game.combat_stats import calc_crit_chance
    # LCK=10, enemy_level=10 → 10/(10*4) = 0.25
    assert calc_crit_chance(luck=10, enemy_level=10) == pytest.approx(0.25)

def test_crit_chance_capped():
    from game.combat_stats import calc_crit_chance
    assert calc_crit_chance(luck=1000, enemy_level=1) == pytest.approx(0.50)

def test_hp_for_class():
    from game.combat_stats import calc_hp
    assert calc_hp("warrior", endurance=15, level=10) == 825
    assert calc_hp("mage",    endurance=8,  level=10) == 176
    assert calc_hp("ranger",  endurance=12, level=10) == 528
