"""
tests/test_combat.py — Unit testy pro bojovou logiku (game/combat_engine.py)
Čisté testy bez DB nebo HTTP.
"""
import pytest
from unittest.mock import patch

from game.combat_engine import (
    CombatantConfig,
    CombatResult,
    simulate_unified_combat,
    calculate_win_chance,
    _crit_chance,
    _calc_damage,
    _FighterState,
)


def _player(hp=825, weapon_dmg=20, armor_value=50, luck=5, level=5):
    return CombatantConfig(
        name="Hrdina", hp=hp, weapon_dmg=weapon_dmg,
        armor_value=armor_value, primary_stat=20,
        secondary_a=10, secondary_b=5,
        luck=luck, level=level, cls="warrior",
    )


def _enemy(hp=80, weapon_dmg=12, armor_value=10, luck=3, level=3):
    return CombatantConfig(
        name="Skřet", hp=hp, weapon_dmg=weapon_dmg,
        armor_value=armor_value, primary_stat=10,
        secondary_a=5, secondary_b=3,
        luck=luck, level=level, cls="",
    )


# ── _crit_chance ──────────────────────────────────────────────────────────────

def test_crit_chance_minimum():
    assert _crit_chance(luck=0) == pytest.approx(0.05)


def test_crit_chance_maximum():
    assert _crit_chance(luck=100) == pytest.approx(0.40)


def test_crit_chance_scales_with_luck():
    assert _crit_chance(luck=10) > _crit_chance(luck=0)
    assert _crit_chance(luck=30) > _crit_chance(luck=10)


# ── _calc_damage ──────────────────────────────────────────────────────────────

def test_calc_damage_no_crit():
    """New _calc_damage uses attacker/defender FighterState objects with armor formula."""
    attacker = _FighterState(_player(weapon_dmg=20))
    defender = _FighterState(_enemy(armor_value=10))
    with patch("game.combat_engine.random") as mock_rng:
        mock_rng.uniform.return_value = 1.0
        dmg = _calc_damage(attacker, defender, is_crit=False)
    assert dmg >= 1


def test_calc_damage_crit_multiplier():
    attacker = _FighterState(_player(weapon_dmg=20))
    defender = _FighterState(_enemy(armor_value=0))
    with patch("game.combat_engine.random") as mock_rng:
        mock_rng.uniform.return_value = 1.0
        normal = _calc_damage(attacker, defender, is_crit=False)
        crit   = _calc_damage(attacker, defender, is_crit=True)
    assert crit > normal


def test_calc_damage_minimum_one():
    attacker = _FighterState(_player(weapon_dmg=1))
    defender = _FighterState(_enemy(armor_value=9999))
    with patch("game.combat_engine.random") as mock_rng:
        mock_rng.uniform.return_value = 0.85
        dmg = _calc_damage(attacker, defender, is_crit=False)
    assert dmg >= 1


# ── simulate_unified_combat ───────────────────────────────────────────────────

def test_simulate_combat_player_wins():
    player = _player(hp=1000, weapon_dmg=200, armor_value=100)
    enemy  = _enemy(hp=5, weapon_dmg=1, armor_value=0)
    result = simulate_unified_combat(player, enemy)
    assert result.attacker_won is True
    assert result.attacker_hp_remaining > 0
    assert isinstance(result.log, list)
    assert len(result.log) > 0


def test_simulate_combat_enemy_wins():
    player = _player(hp=5, weapon_dmg=1, armor_value=0)
    enemy  = _enemy(hp=1000, weapon_dmg=200, armor_value=100)
    result = simulate_unified_combat(player, enemy)
    assert result.attacker_won is False
    assert result.attacker_hp_remaining == 0


def test_simulate_combat_timeout_resolved_by_hp():
    # Oba nezranitelní → timeout → vítěz dle HP%
    player = _player(hp=1000, weapon_dmg=1, armor_value=9999)
    enemy  = _enemy(hp=100, weapon_dmg=1, armor_value=9999)
    result = simulate_unified_combat(player, enemy, max_rounds=3)
    assert result.rounds == 3
    assert result.attacker_won is True  # více HP%


def test_simulate_combat_returns_correct_types():
    result = simulate_unified_combat(_player(), _enemy())
    assert isinstance(result, CombatResult)
    assert result.attacker_won in (True, False)
    assert result.rounds >= 1
    assert isinstance(result.attacker_hp_remaining, int)


# ── _quest_enemy_config — inline logika (testujeme formuli přímo) ─────────────

def _quest_enemy_config(qdef, character_level):
    difficulty = qdef[3]
    base_level = max(qdef[8], character_level)
    mult = {"easy": 0.75, "normal": 1.0, "hard": 1.35, "boss": 2.0}.get(difficulty, 1.0)
    _atk = int(8 * base_level * mult)
    _def = int(4 * base_level * mult)
    _spd = int(6 * base_level * mult * 0.8)
    return CombatantConfig(
        name=f"[{qdef[1]}] Nepřítel",
        hp=int(50 * base_level * mult),
        weapon_dmg=_atk, armor_value=_def,
        primary_stat=_atk, secondary_a=_spd, secondary_b=5,
        luck=int(3 * mult),
        level=base_level,
        cls="",
    )


def test_quest_enemy_stats_easy():
    quest = (1, "Skřeti v lese", "desc", "easy", 2, 40, 15, 30, 1, "🌲")
    enemy = _quest_enemy_config(quest, character_level=5)
    assert enemy.hp == int(50 * 5 * 0.75)
    assert enemy.weapon_dmg == int(8 * 5 * 0.75)
    assert enemy.level == 5


def test_quest_enemy_stats_boss():
    quest = (10, "BOSS: Kostěný král", "desc", "boss", 20, 600, 300, 500, 10, "💀")
    enemy = _quest_enemy_config(quest, character_level=10)
    assert enemy.hp == int(50 * 10 * 2.0)
    assert enemy.weapon_dmg == int(8 * 10 * 2.0)
    assert enemy.level == 10


def test_quest_enemy_uses_min_level_when_higher():
    quest = (11, "High Quest", "desc", "hard", 15, 300, 100, 200, 15, "⚔️")
    enemy = _quest_enemy_config(quest, character_level=5)
    assert enemy.level == 15


# ── calculate_win_chance ──────────────────────────────────────────────────────

def test_calculate_win_chance_strong_player():
    strong = _player(hp=1000, weapon_dmg=200, armor_value=100)
    weak   = _enemy(hp=10, weapon_dmg=1, armor_value=0)
    assert calculate_win_chance(strong, weak) >= 0.9


def test_calculate_win_chance_weak_player():
    weak   = _player(hp=10, weapon_dmg=1, armor_value=0)
    strong = _enemy(hp=1000, weapon_dmg=200, armor_value=100)
    assert calculate_win_chance(weak, strong) <= 0.1


def test_calculate_win_chance_range():
    result = calculate_win_chance(_player(), _enemy())
    assert 0.0 <= result <= 1.0
