"""
tests/test_item_model.py — Ověřuje stav Item ORM modelu po stat-system redesignu.
bonus_spd a bonus_mp musí být odstraněny; bonus_xp musí existovat.
"""
from models.item import Item


def test_item_has_no_bonus_spd():
    assert not hasattr(Item, 'bonus_spd') or Item.bonus_spd is None


def test_item_has_no_bonus_mp():
    assert not hasattr(Item, 'bonus_mp') or Item.bonus_mp is None


def test_item_has_bonus_xp():
    # Ověří, že InstrumentedAttribute pro bonus_xp existuje na třídě Item
    assert hasattr(Item, 'bonus_xp')
    assert Item.bonus_xp is not None
