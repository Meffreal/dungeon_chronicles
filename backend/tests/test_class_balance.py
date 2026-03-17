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


from game.combat_engine import _FighterState, CombatantConfig


def _make_warrior_with_regen() -> CombatantConfig:
    return CombatantConfig(
        name="TestWarrior", cls="warrior", level=30,
        hp=1000, weapon_dmg=20, armor_value=50,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
        set_bonuses={"regen_every_round": True},
    )


def test_dragon_scales_regen_limited():
    """Dračí Šupiny 5pc regen musí trvat 10 kol, ne 30."""
    state = _FighterState(_make_warrior_with_regen())
    regen_status = next((s for s in state.statuses if s.name == "regen"), None)
    assert regen_status is not None, "Regen status musí existovat"
    assert regen_status.remaining_rounds == 10


def test_rallying_cry_values_reduced():
    """Rallying Cry musí léčit 10% a mít štít 15%."""
    from game.talents import TALENT_T2_TREE
    rc = next(t for t in TALENT_T2_TREE["warrior"] if t["key"] == "rallying_cry")
    assert rc["effect"]["heal_pct"] == 0.10
    assert rc["effect"]["shield_pct"] == 0.15
