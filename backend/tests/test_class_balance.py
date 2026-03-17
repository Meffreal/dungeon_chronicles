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


def _ranger_vs_tank():
    """Ranger vs. tuhý tank — Ranger přežije 10+ kol."""
    ranger = CombatantConfig(
        name="Ranger", cls="ranger", level=20,
        hp=500, weapon_dmg=30, armor_value=20,
        primary_stat=16, secondary_a=9, secondary_b=8,
        luck=5,
    )
    tank = CombatantConfig(
        name="Tank", cls="warrior", level=20,
        hp=5000, weapon_dmg=5, armor_value=60,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
    )
    return ranger, tank


def test_ranger_multi_hit_round_3():
    """Ranger musí útočit 2× v kole 3 (multi-hit kolo)."""
    from game.combat_engine import simulate_unified_combat
    ranger, tank = _ranger_vs_tank()
    result = simulate_unified_combat(ranger, tank, seed=99)
    attack_events_round3 = [
        e for e in result.events
        if e.round == 3
        and e.type in ("attack", "crit", "multi_hit", "ability")
        and e.actor == "Ranger"
    ]
    assert len(attack_events_round3) >= 2, (
        f"Ranger musí útočit 2× v kole 3 (multi-hit), "
        f"ale měl jen {len(attack_events_round3)} event"
    )


def test_ranger_chain_hit_or_multi_fires_over_10_rounds():
    """Za 10 kol musí existovat aspoň jeden chain_hit nebo multi_hit event od Rangera."""
    from game.combat_engine import simulate_unified_combat
    ranger, tank = _ranger_vs_tank()
    result = simulate_unified_combat(ranger, tank, seed=42)
    chain_events = [
        e for e in result.events
        if e.type in ("chain_hit", "multi_hit") and e.actor == "Ranger"
    ]
    assert len(chain_events) > 0, (
        "Za 10+ kol musí Ranger mít aspoň jeden chain/multi-hit event"
    )


def _mage_vs_tank():
    mage = CombatantConfig(
        name="Mage", cls="mage", level=20,
        hp=400, weapon_dmg=25, armor_value=10,
        primary_stat=18, secondary_a=5, secondary_b=8,
        luck=10,
    )
    tank = CombatantConfig(
        name="Tank", cls="warrior", level=20,
        hp=5000, weapon_dmg=5, armor_value=60,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
    )
    return mage, tank


def test_mage_applies_spell_burn_after_attack():
    """Mage musí aplikovat burn DoT na nepřítele po každém útoku."""
    from game.combat_engine import simulate_unified_combat
    mage, tank = _mage_vs_tank()
    result = simulate_unified_combat(mage, tank, seed=1)
    burn_events = [e for e in result.events if e.type == "burn"]
    assert len(burn_events) > 0, "Mage musí způsobit burn DoT (type='burn')"


def test_mage_spirit_revenge_on_round1_death():
    """Mage zabitý v kole 1 musí způsobit Spirit Revenge damage útočníkovi."""
    import pytest
    mage_1hp = CombatantConfig(
        name="Mage", cls="mage", level=1,
        hp=1, weapon_dmg=5, armor_value=1,
        primary_stat=5, secondary_a=3, secondary_b=3,
        luck=5,
    )
    killer = CombatantConfig(
        name="Warrior", cls="warrior", level=20,
        hp=1000, weapon_dmg=50, armor_value=80,
        primary_stat=15, secondary_a=8, secondary_b=5,
        luck=5,
    )
    from game.combat_engine import simulate_unified_combat
    result = simulate_unified_combat(killer, mage_1hp, seed=1)
    spirit_events = [e for e in result.events if e.type == "spirit_revenge"]
    assert len(spirit_events) > 0, "Spirit Revenge event musí existovat"
    sr = spirit_events[0]
    # 20% z 1000 = 200
    assert sr.damage == pytest.approx(200, abs=5)
