"""
tests/test_arena.py — Unit testy pro PvP arénu a ELO systém
Čisté testy bez DB nebo HTTP.
"""
from game.combat_engine import CombatantConfig, simulate_unified_combat, events_to_dict_list


# ── ELO logika (inline z routers/arena.py) ────────────────────────────────────

_ELO_K = 32


def _calc_elo_change(attacker_elo: int, defender_elo: int,
                     attacker_won: bool) -> tuple[int, int]:
    expected_a = 1 / (1 + 10 ** ((defender_elo - attacker_elo) / 400))
    actual_a   = 1.0 if attacker_won else 0.0
    change_a   = int(_ELO_K * (actual_a - expected_a))
    change_d   = int(_ELO_K * ((1.0 - actual_a) - (1.0 - expected_a)))
    change_a   = max(3, change_a)  if attacker_won     else min(-3, change_a)
    change_d   = max(3, change_d)  if not attacker_won else min(-3, change_d)
    return change_a, change_d


def _fighter(name="Fighter", hp=200, atk=30, def_=15, luck=10, level=5):
    return CombatantConfig(
        name=name, hp=hp,
        weapon_dmg=atk, armor_value=def_,
        primary_stat=atk, secondary_a=10, secondary_b=5,
        luck=luck, level=level, cls="",
    )


# ── simulate_unified_combat (PvP) ─────────────────────────────────────────────

def test_pvp_fight_returns_required_attrs():
    result = simulate_unified_combat(_fighter("A"), _fighter("B"), max_rounds=20)
    assert hasattr(result, "attacker_won")
    assert hasattr(result, "attacker_hp_remaining")
    assert hasattr(result, "defender_hp_remaining")
    assert hasattr(result, "rounds")
    assert hasattr(result, "log")


def test_pvp_fight_winner_is_bool():
    result = simulate_unified_combat(_fighter("Útočník"), _fighter("Obránce"), max_rounds=20)
    assert isinstance(result.attacker_won, bool)


def test_pvp_fight_strong_attacker_wins():
    goliath  = _fighter("Goliáš",  hp=2000, atk=500, def_=200)
    weakling = _fighter("Slaboch", hp=10,   atk=1,   def_=0)
    result   = simulate_unified_combat(goliath, weakling, max_rounds=20)
    assert result.attacker_won is True


def test_pvp_fight_weak_attacker_loses():
    weakling = _fighter("Slaboch", hp=10,   atk=1,   def_=0)
    goliath  = _fighter("Goliáš",  hp=2000, atk=500, def_=200)
    result   = simulate_unified_combat(weakling, goliath, max_rounds=20)
    assert result.attacker_won is False


def test_pvp_fight_hp_remaining_nonnegative():
    result = simulate_unified_combat(_fighter("A"), _fighter("B"), max_rounds=20)
    assert result.attacker_hp_remaining >= 0
    assert result.defender_hp_remaining >= 0


def test_pvp_fight_battle_log_is_list():
    result = simulate_unified_combat(_fighter("A"), _fighter("B"), max_rounds=20)
    assert isinstance(result.log, list)
    assert len(result.log) > 0


def test_pvp_fight_events_serializable():
    result = simulate_unified_combat(_fighter("A"), _fighter("B"), max_rounds=20)
    events = events_to_dict_list(result.events)
    assert isinstance(events, list)


# ── _calc_elo_change ──────────────────────────────────────────────────────────

def test_elo_attacker_gains_on_win():
    atk_change, def_change = _calc_elo_change(1000, 1000, attacker_won=True)
    assert atk_change > 0
    assert def_change < 0


def test_elo_attacker_loses_on_loss():
    atk_change, def_change = _calc_elo_change(1000, 1000, attacker_won=False)
    assert atk_change < 0
    assert def_change > 0


def test_elo_minimum_change_on_win():
    atk_change, def_change = _calc_elo_change(3000, 100, attacker_won=True)
    assert atk_change >= 3
    assert abs(def_change) >= 3


def test_elo_minimum_change_on_loss():
    atk_change, def_change = _calc_elo_change(100, 3000, attacker_won=False)
    assert abs(atk_change) >= 3
    assert def_change >= 3


def test_elo_underdog_wins_bigger_gain():
    atk_underdog, _ = _calc_elo_change(800,  1200, attacker_won=True)
    atk_favorite, _ = _calc_elo_change(1200, 800,  attacker_won=True)
    assert atk_underdog > atk_favorite
