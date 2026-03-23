"""Tests for dungeon_boss_logic pure functions."""
import pytest
from datetime import datetime, timezone
from game.dungeon_boss_logic import (
    get_boss_def,
    is_milestone_boss,
    get_item_tier,
    get_milestone_item,
    build_boss_enemy,
    calc_boss_rewards,
    check_dungeon_unlocked,
    boss_cooldown_until,
)


def test_get_boss_def_valid():
    boss = get_boss_def("tomb_of_forgotten", 1)
    assert boss is not None
    assert boss["num"] == 1
    assert "Ashbone Crawler" in boss["name"]


def test_get_boss_def_invalid():
    assert get_boss_def("tomb_of_forgotten", 99) is None
    assert get_boss_def("nonexistent", 1) is None


def test_milestone_boss():
    assert is_milestone_boss(5) is True
    assert is_milestone_boss(10) is True
    assert is_milestone_boss(50) is True
    assert is_milestone_boss(1) is False
    assert is_milestone_boss(7) is False


def test_item_tier():
    assert get_item_tier(5)  == 0
    assert get_item_tier(10) == 0
    assert get_item_tier(15) == 1
    assert get_item_tier(20) == 1
    assert get_item_tier(25) == 2
    assert get_item_tier(30) == 2
    assert get_item_tier(35) == 3
    assert get_item_tier(40) == 3
    assert get_item_tier(45) == 4
    assert get_item_tier(50) == 4


def test_get_milestone_item_returns_correct_class():
    item = get_milestone_item("tomb_of_forgotten", "warrior", 5)
    assert item is not None
    assert item[17] == "warrior"  # hint_class


def test_get_milestone_item_non_milestone_returns_none():
    assert get_milestone_item("tomb_of_forgotten", "warrior", 3) is None


def test_build_boss_enemy_scales_with_boss_num():
    boss1 = build_boss_enemy("tomb_of_forgotten", 1, 10)
    boss50 = build_boss_enemy("tomb_of_forgotten", 50, 10)
    assert boss50.hp > boss1.hp
    assert boss50.weapon_dmg > boss1.weapon_dmg


def test_build_boss_enemy_milestone_is_boss():
    boss5 = build_boss_enemy("tomb_of_forgotten", 5, 10)
    boss3 = build_boss_enemy("tomb_of_forgotten", 3, 10)
    assert boss5.is_boss is True
    assert boss3.is_boss is False


def test_calc_boss_rewards_scale_with_boss_num():
    r1 = calc_boss_rewards("tomb_of_forgotten", 1, 10)
    r50 = calc_boss_rewards("tomb_of_forgotten", 50, 10)
    assert r50["xp"] > r1["xp"]
    assert r50["gold"] > r1["gold"]


def test_check_dungeon_unlocked_first_dungeon():
    unlocked, reason = check_dungeon_unlocked(
        "tomb_of_forgotten", char_level=8, progress_map={}, completed_chain_ids=[]
    )
    assert unlocked is True
    assert reason == ""


def test_check_dungeon_unlocked_level_too_low():
    unlocked, reason = check_dungeon_unlocked(
        "tomb_of_forgotten", char_level=5, progress_map={}, completed_chain_ids=[]
    )
    assert unlocked is False
    assert "level" in reason.lower()


def test_check_dungeon_unlocked_fiery_requires_prev():
    unlocked, reason = check_dungeon_unlocked(
        "fiery_depths",
        char_level=15,
        progress_map={"tomb_of_forgotten": 10},
        completed_chain_ids=[1],
    )
    assert unlocked is False
    assert "25" in reason


def test_check_dungeon_unlocked_fiery_requires_attunement():
    unlocked, reason = check_dungeon_unlocked(
        "fiery_depths",
        char_level=15,
        progress_map={"tomb_of_forgotten": 25},
        completed_chain_ids=[],
    )
    assert unlocked is False
    assert "attunement" in reason.lower()


def test_check_dungeon_unlocked_fiery_success():
    unlocked, reason = check_dungeon_unlocked(
        "fiery_depths",
        char_level=15,
        progress_map={"tomb_of_forgotten": 25},
        completed_chain_ids=[1],
    )
    assert unlocked is True
    assert reason == ""


def test_boss_cooldown_until():
    now = datetime(2026, 1, 1, 12, 0, 0)
    result = boss_cooldown_until(now)
    assert result.hour == 13  # 1 hour later
