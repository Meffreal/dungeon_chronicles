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


def test_weighted_pool_favors_matching_class():
    """Matching class items musí konzistentně dominovat poolu."""
    from unittest.mock import MagicMock
    import random
    from routers.shop import _weighted_pool

    def make_item(id_, hint):
        m = MagicMock()
        m.id = id_
        m.hint_class = hint
        return m

    items = (
        [make_item(i, "warrior") for i in range(10)] +
        [make_item(i + 10, "ranger") for i in range(10)] +
        [make_item(i + 20, None) for i in range(10)]
    )

    warrior_wins = 0
    for seed in range(20):
        rng = random.Random(seed)
        pool = _weighted_pool(items, k=10, char_cls="warrior", rng=rng)
        warrior_count = sum(1 for i in pool if i.hint_class == "warrior")
        ranger_count  = sum(1 for i in pool if i.hint_class == "ranger")
        if warrior_count > ranger_count * 2:
            warrior_wins += 1

    assert warrior_wins >= 16, f"Váhování nefunguje: warrior dominoval jen {warrior_wins}/20 seedů"


def test_weighted_pool_no_duplicates():
    """Pool nesmí obsahovat duplicitní itemy."""
    from unittest.mock import MagicMock
    import random
    from routers.shop import _weighted_pool

    def make_item(id_, hint):
        m = MagicMock()
        m.id = id_
        m.hint_class = hint
        return m

    items = [make_item(i, "warrior" if i < 5 else None) for i in range(15)]
    rng = random.Random(99)
    pool = _weighted_pool(items, k=8, char_cls="warrior", rng=rng)

    ids = [i.id for i in pool]
    assert len(ids) == len(set(ids)), "Pool obsahuje duplicitní itemy"
