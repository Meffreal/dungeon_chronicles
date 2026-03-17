"""
tests/test_character_stats.py — Unit testy pro novou HP formuli v recalculate_stats().
"""
from models.character import Character, CharacterClass


def _make_char(cls, end=10, level=1, **kwargs):
    c = Character(
        cls=cls,
        level=level,
        strength=kwargs.get('strength', 10),
        dexterity=kwargs.get('dexterity', 10),
        intelligence=kwargs.get('intelligence', 10),
        endurance=end,
        luck=kwargs.get('luck', 5),
        prestige_level=0,
        subclass="",
        talents_json="[]",
        active_buffs_json=None,
    )
    return c


def test_warrior_hp_formula():
    c = _make_char("warrior", end=15, level=10)
    c.recalculate_stats()
    assert c.hp_max == 15 * 5 * (10 + 1)  # 825


def test_mage_hp_formula():
    c = _make_char("mage", end=8, level=10)
    c.recalculate_stats()
    assert c.hp_max == 8 * 2 * (10 + 1)  # 176


def test_ranger_hp_formula():
    c = _make_char("ranger", end=12, level=10)
    c.recalculate_stats()
    assert c.hp_max == 12 * 4 * (10 + 1)  # 528


def test_hp_floor():
    c = _make_char("mage", end=0, level=1)
    c.recalculate_stats()
    assert c.hp_max >= 10


def test_no_atk_attribute():
    c = _make_char("warrior", end=10, level=1)
    c.recalculate_stats()
    # recalculate_stats by neměla nastavovat c.atk
    assert not hasattr(c, 'atk') or c.atk is None


def test_no_mp_max_attribute():
    c = _make_char("mage", end=10, level=1)
    c.recalculate_stats()
    assert not hasattr(c, 'mp_max') or c.mp_max is None
