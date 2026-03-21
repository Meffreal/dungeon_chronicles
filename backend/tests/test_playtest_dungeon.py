# backend/tests/test_playtest_dungeon.py
import pytest
import random
from game.playtest_dungeon import (
    generate_map, get_available_nodes, unlock_successors,
    roll_relics, PLAYTEST_DUNGEONS, RELIC_POOL,
)


def test_generate_map_has_required_node_types():
    mdata = generate_map("pt_tomb", char_level=10)
    types = [n["type"] for n in mdata["nodes"].values()]
    assert "boss"   in types
    assert "elite"  in types
    assert "rest"   in types
    assert "start"  in mdata["nodes"]
    assert "n_boss" in mdata["nodes"]


def test_generate_map_constraint_rest():
    """Every map must have at least one rest node."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "rest" in types, f"Missing rest node: {types}"


def test_generate_map_constraint_elite():
    """Every map must have at least one elite node."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "elite" in types, f"Missing elite node: {types}"


def test_available_nodes_initially_layer1():
    """After entering, only layer 1 nodes (n1a, n1b) are available."""
    mdata = generate_map("pt_tomb", char_level=10)
    available = get_available_nodes(mdata)
    assert set(available) == {"n1a", "n1b"}


def test_unlock_successors():
    mdata = generate_map("pt_tomb", char_level=10)
    mdata["nodes"]["n1a"]["status"] = "completed"
    unlock_successors(mdata, "n1a")
    available = get_available_nodes(mdata)
    # n1a edges: ["n1a", "n2a"] and ["n1a", "n2b"] — both n2a and n2b must unlock
    assert "n2a" in available and "n2b" in available


def test_roll_relics_no_duplicates():
    """roll_relics must not return relics the player already has."""
    existing = ["blood_stone", "stone_shield"]
    relics = roll_relics(existing, count=3)
    ids = [r["id"] for r in relics]
    assert "blood_stone"  not in ids
    assert "stone_shield" not in ids
    assert len(relics) == 3


def test_roll_relics_count():
    relics = roll_relics([], count=3)
    assert len(relics) == 3


def test_generate_map_constraint_event():
    """Every map must have at least one event node."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "event" in types, f"Missing event node: {types}"


def test_all_dungeon_keys_valid():
    for key in ["pt_tomb", "pt_fiery", "pt_citadel"]:
        mdata = generate_map(key, char_level=15)
        assert "n_boss" in mdata["nodes"]
