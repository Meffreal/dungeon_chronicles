import pytest
from models.item import Item
from game.seed import SEED_CLASS_ITEMS


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


def test_seed_class_items_count():
    assert len(SEED_CLASS_ITEMS) == 30


def test_seed_class_items_per_class():
    warriors = [i for i in SEED_CLASS_ITEMS if i[-1] == "warrior"]
    rangers  = [i for i in SEED_CLASS_ITEMS if i[-1] == "ranger"]
    mages    = [i for i in SEED_CLASS_ITEMS if i[-1] == "mage"]
    assert len(warriors) == 10
    assert len(rangers)  == 10
    assert len(mages)    == 10


def test_seed_class_items_hint_class_values():
    valid = {"warrior", "ranger", "mage"}
    for item in SEED_CLASS_ITEMS:
        assert item[-1] in valid, f"Neplatný hint_class: {item[-1]}"
