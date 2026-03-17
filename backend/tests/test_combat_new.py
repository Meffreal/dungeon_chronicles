import pytest
from game.combat_engine import CombatantConfig, simulate_unified_combat


def _warrior(hp=825, weapon_dmg=20, armor_value=90,
             str_=30, dex=10, int_=5, luck=5, level=10):
    return CombatantConfig(
        name="Warrior", hp=hp,
        weapon_dmg=weapon_dmg, armor_value=armor_value,
        primary_stat=str_, secondary_a=dex, secondary_b=int_,
        luck=luck, level=level, cls="warrior",
    )


def _mage(hp=176, weapon_dmg=20, armor_value=20,
          str_=5, dex=8, int_=30, luck=8, level=10):
    return CombatantConfig(
        name="Mage", hp=hp,
        weapon_dmg=weapon_dmg, armor_value=armor_value,
        primary_stat=int_, secondary_a=str_, secondary_b=dex,
        luck=luck, level=level, cls="mage",
    )


def test_combatant_config_no_atk_field():
    w = _warrior()
    assert not hasattr(w, 'atk')


def test_combatant_config_no_strategy_field():
    w = _warrior()
    assert not hasattr(w, 'strategy')


def test_combat_runs_warrior_vs_mage():
    result = simulate_unified_combat(_warrior(), _mage())
    assert result.winner in ("attacker", "defender")
    assert result.rounds >= 1


def test_ranger_always_first_strike():
    ranger_cfg = CombatantConfig(
        name="Ranger", hp=528, weapon_dmg=20, armor_value=50,
        primary_stat=30, secondary_a=9, secondary_b=8,
        luck=13, level=10, cls="ranger",
    )
    warrior_cfg = CombatantConfig(
        name="Warrior", hp=825, weapon_dmg=20, armor_value=90,
        primary_stat=30, secondary_a=10, secondary_b=5,
        luck=5, level=10, cls="warrior",
    )
    result = simulate_unified_combat(ranger_cfg, warrior_cfg)
    first_attack = next(e for e in result.events if e.type in ("attack", "crit", "ability"))
    assert first_attack.actor == "Ranger"
