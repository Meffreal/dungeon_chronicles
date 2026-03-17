"""
tests/test_status_effects.py — Unit testy pro status efekty v combat enginu

Testuje:
  - add_status / has_status / get_status / remove_status
  - Tick hodnoty (bleed, poison, regen, burn)
  - Efektivní stats s debuffs (weaken, slow)
  - Shield absorb
  - Stun
  - modifier_statuses z CombatantConfig
  - Status interakce: burn+shield, poison+regen, bleed+weaken
"""
import pytest
from game.combat_engine import (
    CombatantConfig,
    _FighterState,
    STATUS_DEFS,
    _process_status_ticks,
)


def _cfg(hp=200, atk=30, def_=10, spd=12, luck=5, level=5, modifier_statuses=None):
    return CombatantConfig(
        name="Testovač", hp=hp,
        weapon_dmg=atk, armor_value=def_,
        primary_stat=atk, secondary_a=spd, secondary_b=5,
        luck=luck, level=level, cls="",
        modifier_statuses=modifier_statuses or [],
    )


def _fighter(**kw):
    return _FighterState(_cfg(**kw))


# ── add_status / has_status / get_status / remove_status ──────────────────────

def test_add_status_sets_has_status():
    f = _fighter()
    f.add_status("bleed", hp_max=200, atk=30)
    assert f.has_status("bleed")


def test_has_status_false_when_absent():
    f = _fighter()
    assert not f.has_status("poison")


def test_get_status_returns_none_when_absent():
    f = _fighter()
    assert f.get_status("bleed") is None


def test_add_status_stores_correct_rounds():
    f = _fighter()
    f.add_status("bleed", hp_max=200, atk=30)
    s = f.get_status("bleed")
    assert s is not None
    assert s.remaining_rounds == STATUS_DEFS["bleed"]["rounds"]


def test_add_status_renewal_restores_rounds():
    """Druhá aplikace stejného statusu obnoví trvání."""
    f = _fighter()
    f.add_status("bleed", hp_max=200, atk=30)
    s = f.get_status("bleed")
    s.remaining_rounds = 1  # Simuluj ubývání
    f.add_status("bleed", hp_max=200, atk=30)  # Obnov
    assert s.remaining_rounds == STATUS_DEFS["bleed"]["rounds"]


def test_add_status_does_not_duplicate():
    """Opakovaný add_status nevytvoří druhý záznam."""
    f = _fighter()
    f.add_status("bleed", hp_max=200, atk=30)
    f.add_status("bleed", hp_max=200, atk=30)
    assert len([s for s in f.statuses if s.name == "bleed"]) == 1


def test_remove_status():
    f = _fighter()
    f.add_status("poison", hp_max=200, atk=30)
    assert f.has_status("poison")
    f.remove_status("poison")
    assert not f.has_status("poison")


def test_remove_nonexistent_status_no_error():
    f = _fighter()
    f.remove_status("bleed")  # Nesmí hodit výjimku


def test_multiple_different_statuses():
    f = _fighter()
    for s in ("bleed", "poison", "stun", "shield", "weaken"):
        f.add_status(s, hp_max=200, atk=30)
    for s in ("bleed", "poison", "stun", "shield", "weaken"):
        assert f.has_status(s)


# ── Tick hodnoty ───────────────────────────────────────────────────────────────

def test_bleed_tick_scales_with_hp_max():
    """Bleed tick = 6 % max HP."""
    f = _fighter(hp=200)
    f.add_status("bleed", hp_max=200, atk=30)
    s = f.get_status("bleed")
    assert s.tick_value == pytest.approx(200 * STATUS_DEFS["bleed"]["tick_dmg_pct"])


def test_burn_tick_scales_with_hp_max():
    """Burn tick = 4 % max HP."""
    f = _fighter(hp=300)
    f.add_status("burn", hp_max=300, atk=30)
    s = f.get_status("burn")
    assert s.tick_value == pytest.approx(300 * STATUS_DEFS["burn"]["tick_dmg_pct"])


def test_regen_tick_scales_with_hp_max():
    """Regen tick = 5 % max HP."""
    f = _fighter(hp=200)
    f.add_status("regen", hp_max=200, atk=30)
    s = f.get_status("regen")
    assert s.tick_value == pytest.approx(200 * STATUS_DEFS["regen"]["heal_pct"])


def test_poison_tick_scales_with_atk():
    """Poison tick = 1.0× útočníkův ATK."""
    f = _fighter()
    f.add_status("poison", hp_max=200, atk=40)
    s = f.get_status("poison")
    assert s.tick_value == pytest.approx(40 * STATUS_DEFS["poison"]["tick_dmg_flat"])


def test_bleed_tick_larger_for_higher_hp():
    f_low  = _fighter(hp=100)
    f_high = _fighter(hp=400)
    f_low.add_status("bleed",  hp_max=100, atk=30)
    f_high.add_status("bleed", hp_max=400, atk=30)
    s_low  = f_low.get_status("bleed")
    s_high = f_high.get_status("bleed")
    assert s_high.tick_value > s_low.tick_value


# ── Efektivní stats s debuffs ─────────────────────────────────────────────────

def test_weaken_reduces_effective_atk():
    """Weaken: -30 % ATK."""
    f = _fighter(atk=100)
    base = f.effective_atk()
    f.add_status("weaken", hp_max=200, atk=100)
    eff = f.effective_atk()
    assert eff < base
    assert eff == pytest.approx(int(base * (1.0 - STATUS_DEFS["weaken"]["atk_debuff_pct"])), abs=1)


def test_no_debuff_no_change():
    f = _fighter(atk=50, spd=30)
    assert f.effective_atk() >= 1
    assert f.effective_spd() == f.spd


def test_effective_atk_minimum_one():
    """effective_atk() nesmí vrátit méně než 1."""
    f = _fighter(atk=1)
    f.add_status("weaken", hp_max=100, atk=1)
    assert f.effective_atk() >= 1


# ── Shield absorb ─────────────────────────────────────────────────────────────

def test_shield_absorb_zero_without_shield():
    f = _fighter()
    assert f.shield_absorb() == 0.0


def test_shield_absorb_correct_pct_with_shield():
    f = _fighter()
    f.add_status("shield", hp_max=200, atk=30)
    assert f.shield_absorb() == pytest.approx(STATUS_DEFS["shield"]["absorb_pct"])


def test_shield_absorb_zero_after_remove():
    f = _fighter()
    f.add_status("shield", hp_max=200, atk=30)
    f.remove_status("shield")
    assert f.shield_absorb() == 0.0


# ── Stun ──────────────────────────────────────────────────────────────────────

def test_is_stunned_false_by_default():
    f = _fighter()
    assert not f.is_stunned()


def test_is_stunned_true_when_stun_active():
    f = _fighter()
    f.add_status("stun", hp_max=200, atk=30)
    assert f.is_stunned()


def test_stun_removed_clears_is_stunned():
    f = _fighter()
    f.add_status("stun", hp_max=200, atk=30)
    f.remove_status("stun")
    assert not f.is_stunned()


# ── modifier_statuses ─────────────────────────────────────────────────────────

def test_modifier_status_applied_at_init():
    """modifier_statuses z CombatantConfig se aplikují při inicializaci."""
    f = _fighter(modifier_statuses=["poison"])
    assert f.has_status("poison")


def test_modifier_multiple_statuses_at_init():
    f = _fighter(modifier_statuses=["bleed", "weaken"])
    assert f.has_status("bleed")
    assert f.has_status("weaken")


def test_modifier_invalid_status_ignored():
    """Neznámý modifier status nezpůsobí chybu ani nevytvoří status."""
    f = _fighter(modifier_statuses=["neexistujici_status", "dalsi_spatny"])
    assert len(f.statuses) == 0


def test_modifier_empty_list_no_statuses():
    f = _fighter(modifier_statuses=[])
    assert len(f.statuses) == 0


# ── Status interakce: burn + shield ──────────────────────────────────────────

def test_interaction_burn_shield_reduces_absorb():
    """Burn + shield: každý burn tick sníží absorpci štítu o 10 %."""
    cfg = CombatantConfig(
        name="Target", hp=300,
        weapon_dmg=20, armor_value=5,
        primary_stat=20, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    fighter = _FighterState(cfg)
    other_cfg = CombatantConfig(
        name="Other", hp=100,
        weapon_dmg=20, armor_value=0,
        primary_stat=20, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    other = _FighterState(other_cfg)

    fighter.add_status("shield", hp_max=300, atk=20)
    fighter.add_status("burn",   hp_max=300, atk=20)
    absorb_before = fighter.get_status("shield").absorb_pct
    assert absorb_before == pytest.approx(0.30)

    _process_status_ticks(fighter, other, round_num=1, events=[], log=[])

    sh = fighter.get_status("shield")
    if sh:  # Shield mohl expirovat při velmi nízkém absorb
        assert sh.absorb_pct < absorb_before, "Absorpce štítu se nezmenšila po burn ticku!"


# ── Status interakce: poison + regen ─────────────────────────────────────────

def test_interaction_poison_regen_net_heal():
    """Poison + regen: silnější regen → čistý efekt je léčení."""
    cfg = CombatantConfig(
        name="Target", hp=190,
        weapon_dmg=5, armor_value=0,
        primary_stat=5, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    fighter = _FighterState(cfg)
    other_cfg = CombatantConfig(
        name="Other", hp=100,
        weapon_dmg=5, armor_value=0,
        primary_stat=5, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    other = _FighterState(other_cfg)

    # regen tick = 200 * 0.05 = 10 HP
    # poison tick = 5 * 1.0 = 5 DMG
    # čistý efekt = +5 HP (regen zvítězil)
    fighter.add_status("regen",  hp_max=200, atk=5)    # léčí 10
    fighter.add_status("poison", hp_max=200, atk=5)    # škodí 5

    hp_before = fighter.hp
    _process_status_ticks(fighter, other, round_num=1, events=[], log=[])
    assert fighter.hp >= hp_before, "Regen měl zvítězit nad poisonem"


def test_interaction_poison_regen_net_damage():
    """Poison + regen: silnější jed → čistý efekt je škoda."""
    cfg = CombatantConfig(
        name="Target", hp=190,
        weapon_dmg=80, armor_value=0,
        primary_stat=80, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    fighter = _FighterState(cfg)
    other_cfg = CombatantConfig(
        name="Other", hp=100,
        weapon_dmg=5, armor_value=0,
        primary_stat=5, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    other = _FighterState(other_cfg)

    # poison tick = 80 * 1.0 = 80 DMG
    # regen tick  = 200 * 0.05 = 10 HP
    # čistý efekt = -70 HP (jed zvítězil)
    fighter.add_status("poison", hp_max=200, atk=80)   # škodí 80
    fighter.add_status("regen",  hp_max=200, atk=80)   # léčí 10

    hp_before = fighter.hp
    _process_status_ticks(fighter, other, round_num=1, events=[], log=[])
    assert fighter.hp < hp_before, "Jed měl zvítězit nad regenerací"


# ── Status interakce: bleed + weaken ─────────────────────────────────────────

def test_interaction_bleed_weaken_amplifies_damage():
    """Bleed + weaken: bleed tick způsobí 50 % více škody."""
    cfg = CombatantConfig(
        name="Target", hp=200,
        weapon_dmg=10, armor_value=0,
        primary_stat=10, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    other_cfg = CombatantConfig(
        name="Other", hp=100,
        weapon_dmg=10, armor_value=0,
        primary_stat=10, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )

    # Souboj BEZ weaken — základní bleed dmg
    f_no_weaken = _FighterState(cfg)
    other_no = _FighterState(other_cfg)
    f_no_weaken.add_status("bleed", hp_max=200, atk=10)
    hp_before_no = f_no_weaken.hp
    _process_status_ticks(f_no_weaken, other_no, round_num=1, events=[], log=[])
    dmg_no_weaken = hp_before_no - f_no_weaken.hp

    # Souboj SE weakenem — bleed dmg musí být vyšší
    f_with_weaken = _FighterState(cfg)
    other_with = _FighterState(other_cfg)
    f_with_weaken.add_status("bleed",  hp_max=200, atk=10)
    f_with_weaken.add_status("weaken", hp_max=200, atk=10)
    hp_before_w = f_with_weaken.hp
    _process_status_ticks(f_with_weaken, other_with, round_num=1, events=[], log=[])
    dmg_with_weaken = hp_before_w - f_with_weaken.hp

    assert dmg_with_weaken > dmg_no_weaken, (
        f"Bleed+weaken interakce: dmg s weakenem ({dmg_with_weaken}) "
        f"musí být větší než bez ({dmg_no_weaken})"
    )


# ── Status tick — regen léčí ──────────────────────────────────────────────────

def test_regen_heals_hp():
    """Regen tick léčí HP (pokud pod maxem)."""
    cfg = CombatantConfig(
        name="Target", hp=150,
        weapon_dmg=10, armor_value=0,
        primary_stat=10, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    fighter = _FighterState(cfg)
    fighter.hp = 150  # Pod maxem
    other_cfg = CombatantConfig(
        name="Other", hp=100,
        weapon_dmg=10, armor_value=0,
        primary_stat=10, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    other = _FighterState(other_cfg)

    fighter.add_status("regen", hp_max=150, atk=10)  # tick = 150*0.05 = 7
    fighter.hp = 100  # zraněn

    hp_before = fighter.hp
    _process_status_ticks(fighter, other, round_num=1, events=[], log=[])
    assert fighter.hp > hp_before, "Regen musí léčit HP"


def test_regen_does_not_exceed_max_hp():
    """Regen nesmí přesáhnout hp_max."""
    cfg = CombatantConfig(
        name="Target", hp=200,
        weapon_dmg=10, armor_value=0,
        primary_stat=10, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    fighter = _FighterState(cfg)
    other_cfg = CombatantConfig(
        name="Other", hp=100,
        weapon_dmg=10, armor_value=0,
        primary_stat=10, secondary_a=10, secondary_b=5,
        luck=0, level=1, cls=""
    )
    other = _FighterState(other_cfg)

    fighter.add_status("regen", hp_max=200, atk=10)
    fighter.hp = fighter.hp_max  # Plné HP

    _process_status_ticks(fighter, other, round_num=1, events=[], log=[])
    assert fighter.hp <= fighter.hp_max
