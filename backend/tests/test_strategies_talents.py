"""
tests/test_strategies_talents.py — Unit testy pro combat strategie a talent efekty

Testuje:
  - Aggro / defensive / burst / balanced strategie — stat multiplikátory
  - Defensive start štít
  - Neznámá strategie → balanced fallback
  - Talenty: fortitude, mana_surge, eagle_eye, battle_rage, iron_skin,
             arcane_focus, spell_echo, evasion, hunters_mark
  - Kombinace více talentů
"""
import pytest
from game.combat_engine import (
    CombatantConfig,
    _FighterState,
    soft_cap_stat,
)


def _cfg(strategy="balanced", talents=None,
         hp=200, atk=100, def_=50, spd=60, mp=100, luck=20, level=10):
    return CombatantConfig(
        name="Testovač", hp=hp, atk=atk, def_=def_, spd=spd,
        luck=luck, level=level, cls="warrior", mp=mp,
        strategy=strategy,
        talents=talents or [],
    )


def _f(**kw):
    return _FighterState(_cfg(**kw))


# ── Strategie: Balanced ────────────────────────────────────────────────────────

def test_balanced_stats_match_soft_cap():
    """Balanced nemění stats — výsledek je jen soft_cap(raw)."""
    f = _f(strategy="balanced", atk=100, def_=50, spd=60)
    assert f.atk  == max(1, int(soft_cap_stat(100) * 1.00))
    assert f.def_ == max(0, int(soft_cap_stat(50)  * 1.00))
    assert f.spd  == max(1, int(soft_cap_stat(60)  * 1.00))


def test_balanced_no_start_status():
    f = _f(strategy="balanced")
    assert len(f.statuses) == 0


# ── Strategie: Aggro ──────────────────────────────────────────────────────────

def test_aggro_higher_atk_than_balanced():
    balanced = _f(strategy="balanced", atk=100)
    aggro    = _f(strategy="aggro",    atk=100)
    assert aggro.atk > balanced.atk


def test_aggro_higher_spd_than_balanced():
    balanced = _f(strategy="balanced", spd=60)
    aggro    = _f(strategy="aggro",    spd=60)
    assert aggro.spd > balanced.spd


def test_aggro_lower_def_than_balanced():
    balanced = _f(strategy="balanced", def_=50)
    aggro    = _f(strategy="aggro",    def_=50)
    assert aggro.def_ < balanced.def_


def test_aggro_no_start_status():
    f = _f(strategy="aggro")
    assert not f.has_status("shield")


def test_aggro_atk_mult():
    """Aggro: ATK × 1.25 (po soft_cap)."""
    f = _f(strategy="aggro", atk=40)  # zóna 1 → soft_cap(40) = 40
    assert f.atk == max(1, int(40 * 1.25))


def test_aggro_def_mult():
    """Aggro: DEF × 0.85 (po soft_cap)."""
    f = _f(strategy="aggro", def_=40)
    assert f.def_ == max(0, int(40 * 0.85))


# ── Strategie: Defensive ──────────────────────────────────────────────────────

def test_defensive_higher_def_than_balanced():
    balanced  = _f(strategy="balanced",  def_=50)
    defensive = _f(strategy="defensive", def_=50)
    assert defensive.def_ > balanced.def_


def test_defensive_lower_atk_than_balanced():
    balanced  = _f(strategy="balanced",  atk=100)
    defensive = _f(strategy="defensive", atk=100)
    assert defensive.atk < balanced.atk


def test_defensive_starts_with_shield():
    """Defensive strategie: bojovník začíná se štítem."""
    f = _f(strategy="defensive")
    assert f.has_status("shield"), "Defensive strategie musí dát start štít!"


def test_defensive_def_mult():
    """Defensive: DEF × 1.30 (po soft_cap)."""
    f = _f(strategy="defensive", def_=40)
    assert f.def_ == max(0, int(40 * 1.30))


# ── Strategie: Burst ──────────────────────────────────────────────────────────

def test_burst_higher_mp_than_balanced():
    balanced = _f(strategy="balanced", mp=100)
    burst    = _f(strategy="burst",    mp=100)
    assert burst.mp > balanced.mp


def test_burst_higher_atk_than_balanced():
    balanced = _f(strategy="balanced", atk=100)
    burst    = _f(strategy="burst",    atk=100)
    assert burst.atk > balanced.atk


def test_burst_mp_mult():
    """Burst: MP × 1.50."""
    f = _f(strategy="burst", mp=100)
    assert f.mp == int(100 * 1.50)


def test_burst_no_start_status():
    f = _f(strategy="burst")
    assert not f.has_status("shield")


# ── Neznámá strategie → balanced fallback ────────────────────────────────────

def test_unknown_strategy_falls_back_to_balanced():
    balanced = _f(strategy="balanced", atk=40, def_=40, spd=40)
    unknown  = _f(strategy="neexistujici", atk=40, def_=40, spd=40)
    assert unknown.atk  == balanced.atk
    assert unknown.def_ == balanced.def_
    assert unknown.spd  == balanced.spd


def test_none_strategy_falls_back_to_balanced():
    cfg = CombatantConfig(
        name="X", hp=200, atk=40, def_=20, spd=30,
        luck=5, level=5, cls="", mp=50, strategy=None,
    )
    f        = _FighterState(cfg)
    balanced = _f(strategy="balanced", atk=40, def_=20, spd=30, mp=50)
    assert f.atk  == balanced.atk
    assert f.def_ == balanced.def_


# ── Talent: fortitude (+15 % HP) ─────────────────────────────────────────────

def test_fortitude_increases_hp():
    f_no   = _f(hp=200, talents=[])
    f_fort = _f(hp=200, talents=["fortitude"])
    assert f_fort.hp     == int(200 * 1.15)
    assert f_fort.hp_max == int(200 * 1.15)
    assert f_fort.hp     > f_no.hp


# ── Talent: mana_surge (+25 % MP) ────────────────────────────────────────────

def test_mana_surge_increases_mp():
    f_no = _f(mp=100, talents=[])
    f_ms = _f(mp=100, talents=["mana_surge"])
    assert f_ms.mp > f_no.mp
    assert f_ms.mp == int(100 * 1.25)


# ── Talent: eagle_eye (+8 LUCK) ──────────────────────────────────────────────

def test_eagle_eye_increases_luck():
    f_no = _f(luck=20, talents=[])
    f_ee = _f(luck=20, talents=["eagle_eye"])
    assert f_ee.luck == soft_cap_stat(20 + 8)
    assert f_ee.luck > f_no.luck


def test_eagle_eye_respects_soft_cap():
    """Eagle Eye přepočítá luck přes soft_cap (i po přičtení 8)."""
    f = _f(luck=150, talents=["eagle_eye"])
    expected = soft_cap_stat(150 + 8)
    assert f.luck == expected


# ── Talent: battle_rage (crit_dmg_bonus_pct = 0.25) ─────────────────────────

def test_battle_rage_sets_crit_dmg_bonus():
    f_no = _f(talents=[])
    f_br = _f(talents=["battle_rage"])
    assert f_no.crit_dmg_bonus_pct == 0.0
    assert f_br.crit_dmg_bonus_pct == pytest.approx(0.25)


# ── Talent: iron_skin (dmg_reduction_pct = 0.20) ────────────────────────────

def test_iron_skin_sets_dmg_reduction():
    f_no = _f(talents=[])
    f_is = _f(talents=["iron_skin"])
    assert f_no.dmg_reduction_pct == 0.0
    assert f_is.dmg_reduction_pct == pytest.approx(0.20)


# ── Talent: arcane_focus (ability_dmg_bonus_pct = 0.20) ──────────────────────

def test_arcane_focus_sets_ability_bonus():
    f_no = _f(talents=[])
    f_af = _f(talents=["arcane_focus"])
    assert f_no.ability_dmg_bonus_pct == 0.0
    assert f_af.ability_dmg_bonus_pct == pytest.approx(0.20)


# ── Talent: spell_echo (spell_echo_chance = 0.25) ────────────────────────────

def test_spell_echo_sets_chance():
    f_no = _f(talents=[])
    f_se = _f(talents=["spell_echo"])
    assert f_no.spell_echo_chance == 0.0
    assert f_se.spell_echo_chance == pytest.approx(0.25)


# ── Talent: evasion (dodge_bonus_pct = 0.10) ─────────────────────────────────

def test_evasion_sets_dodge_bonus():
    f_no = _f(talents=[])
    f_ev = _f(talents=["evasion"])
    assert f_no.dodge_bonus_pct == 0.0
    assert f_ev.dodge_bonus_pct == pytest.approx(0.10)


# ── Talent: hunters_mark (hunters_mark_active = True) ────────────────────────

def test_hunters_mark_sets_flag():
    f_no = _f(talents=[])
    f_hm = _f(talents=["hunters_mark"])
    assert not f_no.hunters_mark_active
    assert f_hm.hunters_mark_active is True


# ── Kombinace talentů ─────────────────────────────────────────────────────────

def test_multiple_talents_combine():
    """Více talentů najednou — každý funguje nezávisle."""
    f = _f(
        hp=200, mp=100, luck=20,
        talents=["fortitude", "mana_surge", "eagle_eye", "iron_skin", "battle_rage"],
    )
    assert f.hp == int(200 * 1.15)
    assert f.mp == int(100 * 1.25)
    assert f.luck == soft_cap_stat(20 + 8)
    assert f.dmg_reduction_pct     == pytest.approx(0.20)
    assert f.crit_dmg_bonus_pct    == pytest.approx(0.25)


def test_unknown_talent_ignored():
    """Neznámý talent se ignoruje bez chyby."""
    f = _f(talents=["neexistuje", "fortitude"])
    # Fortitude musí fungovat
    assert f.hp == int(200 * 1.15)
    # Žádná výjimka
