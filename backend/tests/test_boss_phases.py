"""
tests/test_boss_phases.py — Unit testy pro boss fázový systém

Testuje:
  - _check_boss_phases: trigger při správném % HP
  - Stat multiplikátory (atk, spd, def, dmg_bonus)
  - Léčení bosse při fázi
  - Aplikace statusu na hráče
  - Přidání nové schopnosti
  - Fáze se triggeruje pouze jednou
  - Non-boss fighter nespustí fáze
  - Plná simulace s fázovým bossem
"""
import pytest
from game.combat_engine import (
    CombatantConfig,
    BossPhase,
    _FighterState,
    _check_boss_phases,
    simulate_unified_combat,
    EVENT_PHASE_CHANGE,
)


def _boss(hp=1000, atk=40, def_=20, spd=10, phases=None, specials=None):
    return CombatantConfig(
        name="Drak", hp=hp, atk=atk, def_=def_, spd=spd,
        luck=5, level=20, cls="", mp=0,
        is_boss=True,
        phases=phases or [],
        special_abilities=specials or [],
    )


def _player(hp=500, atk=30):
    return CombatantConfig(
        name="Hrdina", hp=hp, atk=atk, def_=10, spd=12, luck=5, level=10, cls="", mp=0,
    )


def _make_boss_state(hp_current=1000, hp_max=1000, phases=None):
    boss_cfg = _boss(hp=hp_max, phases=phases)
    boss = _FighterState(boss_cfg)
    boss.hp = hp_current
    return boss


# ── Základní trigger ──────────────────────────────────────────────────────────

def test_phase_not_triggered_above_threshold():
    """Fáze se nesmí triggnout, pokud HP je nad limitem."""
    phase = BossPhase(phase_num=1, trigger_hp_pct=0.50, message="Fáze 2!")
    boss   = _make_boss_state(hp_current=600, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    events, log = [], []

    _check_boss_phases(boss, target, round_num=1, events=events, log=log)
    assert len(events) == 0
    assert 1 not in boss.triggered_phases


def test_phase_triggered_at_threshold():
    """Fáze se musí triggnout, pokud HP <= threshold."""
    phase = BossPhase(phase_num=1, trigger_hp_pct=0.50, message="Fáze 2!")
    boss   = _make_boss_state(hp_current=500, hp_max=1000, phases=[phase])  # přesně 50 %
    target = _FighterState(_player())
    events, log = [], []

    _check_boss_phases(boss, target, round_num=1, events=events, log=log)
    assert len(events) == 1
    assert events[0].type == EVENT_PHASE_CHANGE
    assert 1 in boss.triggered_phases


def test_phase_triggered_below_threshold():
    """Fáze se musí triggnout, pokud HP < threshold."""
    phase = BossPhase(phase_num=1, trigger_hp_pct=0.50, message="Fáze 2!")
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])  # 40 %
    target = _FighterState(_player())
    events, log = [], []

    _check_boss_phases(boss, target, round_num=2, events=events, log=log)
    assert len(events) == 1
    assert events[0].phase_msg == "Fáze 2!"


# ── Stat multiplikátory ───────────────────────────────────────────────────────

def test_phase_applies_atk_multiplier():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Enrage!",
        stat_multipliers={"atk": 2.0},
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    atk_before = boss.atk

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.atk == int(atk_before * 2.0)


def test_phase_applies_spd_multiplier():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Zrychlení!",
        stat_multipliers={"spd": 1.5},
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    spd_before = boss.spd

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.spd == int(spd_before * 1.5)


def test_phase_applies_def_multiplier():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Obrana!",
        stat_multipliers={"def": 1.8},
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    def_before = boss.def_

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.def_ == int(def_before * 1.8)


def test_phase_applies_dmg_bonus():
    """dmg_bonus multiplier: boss.dmg_bonus_pct se navýší."""
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Zuřivost!",
        stat_multipliers={"dmg_bonus": 1.50},  # +50 % dmg bonus
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    assert boss.dmg_bonus_pct == 0.0

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.dmg_bonus_pct == pytest.approx(0.50)


def test_phase_multiple_stat_multipliers():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Multi buff!",
        stat_multipliers={"atk": 1.5, "spd": 1.3},
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    atk_before = boss.atk
    spd_before = boss.spd

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.atk == int(atk_before * 1.5)
    assert boss.spd == int(spd_before * 1.3)


# ── Léčení bosse při fázi ─────────────────────────────────────────────────────

def test_phase_heals_boss():
    heal_pct = 0.20
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Boss se léčí!",
        heal_pct=heal_pct,
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    hp_before = boss.hp
    expected_heal = int(boss.hp_max * heal_pct)

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.hp == min(boss.hp_max, hp_before + expected_heal)


def test_phase_heal_does_not_exceed_max():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Léčení!",
        heal_pct=0.80,  # Velké léčení
    )
    boss   = _make_boss_state(hp_current=450, hp_max=1000, phases=[phase])
    target = _FighterState(_player())

    _check_boss_phases(boss, target, 1, [], [])
    assert boss.hp <= boss.hp_max


# ── Status aplikovaný na hráče ────────────────────────────────────────────────

def test_phase_applies_stun_to_player():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Omráčení!",
        apply_status_to_player="stun",
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())

    assert not target.has_status("stun")
    _check_boss_phases(boss, target, 1, [], [])
    assert target.has_status("stun")


def test_phase_applies_bleed_to_player():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.60, message="Krvácení!",
        apply_status_to_player="bleed",
    )
    boss   = _make_boss_state(hp_current=500, hp_max=1000, phases=[phase])
    target = _FighterState(_player())

    _check_boss_phases(boss, target, 1, [], [])
    assert target.has_status("bleed")


def test_phase_no_status_when_none():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Bez statusu.",
        apply_status_to_player=None,
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())

    _check_boss_phases(boss, target, 1, [], [])
    assert len(target.statuses) == 0


# ── Přidání nové schopnosti ───────────────────────────────────────────────────

def test_phase_adds_new_ability():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Nová schopnost!",
        new_ability="fire_breath",
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())

    assert "fire_breath" not in boss.active_specials
    _check_boss_phases(boss, target, 1, [], [])
    assert "fire_breath" in boss.active_specials


def test_phase_does_not_add_duplicate_ability():
    """Stejná schopnost se nepřidá dvakrát."""
    boss_cfg = _boss(hp=1000, specials=["fire_breath"])
    boss = _FighterState(boss_cfg)
    boss.hp = 400
    target = _FighterState(_player())

    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Nová?",
        new_ability="fire_breath",
    )
    boss.cfg = _boss(hp=1000, phases=[phase], specials=["fire_breath"])

    count_before = boss.active_specials.count("fire_breath")
    _check_boss_phases(boss, target, 1, [], [])
    count_after = boss.active_specials.count("fire_breath")
    assert count_after == count_before  # Nepřidalo druhý výskyt


# ── Fáze se triggeruje pouze jednou ──────────────────────────────────────────

def test_phase_triggers_only_once():
    phase = BossPhase(
        phase_num=1, trigger_hp_pct=0.50, message="Fáze 2!",
        stat_multipliers={"atk": 2.0},
    )
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[phase])
    target = _FighterState(_player())
    events, log = [], []

    atk_after_first = None

    _check_boss_phases(boss, target, 1, events, log)   # Trigger
    atk_after_first = boss.atk
    assert len(events) == 1

    _check_boss_phases(boss, target, 2, events, log)   # Druhý pokus
    assert boss.atk == atk_after_first  # ATK se nezměnil
    assert len(events) == 1             # Stále jen 1 event


# ── Více fází ─────────────────────────────────────────────────────────────────

def test_multiple_phases_trigger_independently():
    phase1 = BossPhase(phase_num=1, trigger_hp_pct=0.70, message="Fáze 2!")
    phase2 = BossPhase(phase_num=2, trigger_hp_pct=0.30, message="Fáze 3!")
    boss   = _make_boss_state(hp_current=650, hp_max=1000, phases=[phase1, phase2])
    target = _FighterState(_player())
    events, log = [], []

    _check_boss_phases(boss, target, 1, events, log)
    assert 1 in boss.triggered_phases
    assert 2 not in boss.triggered_phases
    assert len(events) == 1

    boss.hp = 250
    _check_boss_phases(boss, target, 2, events, log)
    assert 2 in boss.triggered_phases
    assert len(events) == 2


# ── Non-boss fighter ──────────────────────────────────────────────────────────

def test_non_boss_no_phase_trigger():
    """Non-boss fighter nespustí žádnou fázi."""
    cfg = CombatantConfig(
        name="Skřet", hp=100, atk=10, def_=5, spd=5, luck=0, level=1, cls="", mp=0,
        is_boss=False,
        phases=[BossPhase(1, 0.50, "Fáze 2!")],
    )
    fighter = _FighterState(cfg)
    fighter.hp = 30
    target = _FighterState(_player())
    events, log = [], []

    _check_boss_phases(fighter, target, 1, events, log)
    assert len(events) == 0


def test_boss_without_phases_no_events():
    """Boss bez definovaných fází nezpůsobí žádné eventy."""
    boss   = _make_boss_state(hp_current=400, hp_max=1000, phases=[])
    target = _FighterState(_player())
    events, log = [], []

    _check_boss_phases(boss, target, 1, events, log)
    assert len(events) == 0


# ── Plná simulace ─────────────────────────────────────────────────────────────

def test_boss_combat_full_simulation():
    """Boss s fázemi a schopnostmi přežije celou simulaci bez výjimky."""
    phase = BossPhase(
        phase_num=1,
        trigger_hp_pct=0.50,
        message="Boss zuří!",
        stat_multipliers={"atk": 1.5},
        apply_status_to_player="stun",
    )
    boss_cfg = _boss(hp=300, atk=15, phases=[phase], specials=["bone_shatter"])
    player_cfg = _player(hp=500, atk=50)

    result = simulate_unified_combat(player_cfg, boss_cfg, max_rounds=30)
    assert result.attacker_won in (True, False)
    assert result.rounds >= 1
    assert result.attacker_hp_remaining >= 0
    assert result.defender_hp_remaining >= 0


def test_boss_combat_strong_boss_wins():
    """Silný boss musí vyhrát."""
    boss_cfg   = _boss(hp=5000, atk=500, def_=300)
    player_cfg = _player(hp=5, atk=1)

    result = simulate_unified_combat(player_cfg, boss_cfg)
    assert result.attacker_won is False


def test_boss_combat_events_include_phase_change():
    """Event log musí obsahovat EVENT_PHASE_CHANGE, pokud fáze proběhla."""
    phase = BossPhase(
        phase_num=1,
        trigger_hp_pct=0.99,   # Triggeruje ihned (skoro plné HP)
        message="Fáze 2!",
    )
    boss_cfg   = _boss(hp=100, atk=1, def_=0, phases=[phase])
    player_cfg = _player(hp=1000, atk=20)

    result = simulate_unified_combat(player_cfg, boss_cfg, max_rounds=30)
    event_types = [e.type for e in result.events]
    assert EVENT_PHASE_CHANGE in event_types, (
        "Simulace neobsahuje EVENT_PHASE_CHANGE, i když fáze měla být triggernuta!"
    )
