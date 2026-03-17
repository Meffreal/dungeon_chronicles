import pytest
from game.combat_stats import CLASS_WEAPON_BASE, CLASS_ARMOR_CAPS
from game.talents import TALENT_TREE


def test_warrior_armor_cap_reduced():
    assert CLASS_ARMOR_CAPS["warrior"] == 0.35


def test_mage_armor_cap_raised():
    assert CLASS_ARMOR_CAPS["mage"] == 0.20


def test_mage_weapon_base_raised():
    assert CLASS_WEAPON_BASE["mage"] == 5


def test_hunters_mark_reduced():
    assert TALENT_TREE["hunters_mark"]["effect"]["first_strike_bonus_pct"] == 0.50
