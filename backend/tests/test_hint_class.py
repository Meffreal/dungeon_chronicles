import pytest
from models.item import Item


def test_item_hint_class_in_to_dict():
    item = Item(
        name="Test meč", item_type="weapon", rarity="common",
        description="Test", icon="⚔️",
        bonus_atk=5, sell_price=10, min_level=1,
        hint_class="warrior",
    )
    d = item.to_dict()
    assert d["hint_class"] == "warrior"


def test_item_hint_class_none_by_default():
    item = Item(
        name="Generický meč", item_type="weapon", rarity="common",
        description="Test", icon="⚔️",
        bonus_atk=5, sell_price=10, min_level=1,
    )
    d = item.to_dict()
    assert d["hint_class"] is None
