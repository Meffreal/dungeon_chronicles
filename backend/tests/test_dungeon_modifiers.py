"""
tests/test_dungeon_modifiers.py — Unit testy pro dungeon modifikátor helper funkce

Testuje:
  - apply_modifier_to_enemy   — stat násobky, boss-specific multiplikátory
  - apply_modifier_to_player  — stat násobky, SPD nikdy nemodifikováno
  - get_modifier_start_statuses — start statusy pro hráče a nepřítele
  - scale_rewards              — XP a gold multiplikátory
  - MODIFIER_ROTATION / DUNGEON_MODIFIERS — structure validation
"""
import pytest
from game.dungeon_modifiers import (
    apply_modifier_to_enemy,
    apply_modifier_to_player,
    get_modifier_start_statuses,
    scale_rewards,
    DUNGEON_MODIFIERS,
    MODIFIER_ROTATION,
)


# ── Zkratky na modifikátory ───────────────────────────────────────────────────
DM = DUNGEON_MODIFIERS

IRON_FORTRESS    = DM["iron_fortress"]
BERSERKER_RAGE   = DM["berserker_rage"]
SWIFT_PREDATORS  = DM["swift_predators"]
CURSED_GROUNDS   = DM["cursed_grounds"]
ANCIENT_BLESSING = DM["ancient_blessing"]
DOUBLE_LOOT      = DM["double_loot"]
WEAKENED_ENEMIES = DM["weakened_enemies"]
BLOODMOON        = DM["bloodmoon"]
FORTIFIED_BOSSES = DM["fortified_bosses"]
BLESSED_WARRIORS = DM["blessed_warriors"]
CHAOS_WEEK       = DM["chaos_week"]


# ══════════════════════════════════════════════════════════════════════════════
# apply_modifier_to_enemy
# ══════════════════════════════════════════════════════════════════════════════

def test_enemy_none_modifier_returns_original():
    assert apply_modifier_to_enemy(None, 100, 20, 10, 15) == (100, 20, 10, 15)


def test_enemy_iron_fortress_hp_and_def():
    """Iron Fortress: +20 % HP, +50 % DEF."""
    hp, atk, def_, spd = apply_modifier_to_enemy(IRON_FORTRESS, 100, 20, 10, 15)
    assert hp   == int(100 * 1.20)
    assert def_ == int(10  * 1.50)
    assert atk  == 20   # nezměněno
    assert spd  == 15   # nezměněno


def test_enemy_berserker_rage_atk_and_def():
    """Berserker Rage: +40 % ATK, -20 % DEF."""
    hp, atk, def_, spd = apply_modifier_to_enemy(BERSERKER_RAGE, 100, 20, 10, 15)
    assert atk  == int(20 * 1.40)
    assert def_ == int(10 * 0.80)
    assert hp   == 100  # nezměněno


def test_enemy_swift_predators_atk():
    """Swift Predators: +15 % ATK. SPD není modifikováno."""
    hp, atk, def_, spd = apply_modifier_to_enemy(SWIFT_PREDATORS, 100, 20, 10, 15)
    assert atk == int(20 * 1.15)
    assert spd == 15    # SPD beze změny
    assert hp  == 100
    assert def_ == 10


def test_enemy_weakened_enemies():
    """Weakened Enemies: -25 % ATK, -25 % DEF."""
    hp, atk, def_, spd = apply_modifier_to_enemy(WEAKENED_ENEMIES, 100, 20, 10, 15)
    assert atk  == int(20 * 0.75)
    assert def_ == int(10 * 0.75)
    assert hp   == 100


def test_enemy_chaos_week_all_stats():
    """Chaos Week: +20 % ATK, DEF, HP. SPD není modifikováno."""
    hp, atk, def_, spd = apply_modifier_to_enemy(CHAOS_WEEK, 100, 20, 10, 15)
    assert hp   == int(100 * 1.20)
    assert atk  == int(20  * 1.20)
    assert def_ == int(10  * 1.20)
    assert spd  == 15   # SPD beze změny


def test_enemy_no_modifier_means_no_change():
    """Modifikátor bez enemyXxx klíčů nezmění stats."""
    # double_loot nemá enemy_XXX klíče
    hp, atk, def_, spd = apply_modifier_to_enemy(DOUBLE_LOOT, 100, 20, 10, 15)
    assert hp   == 100
    assert atk  == 20
    assert def_ == 10
    assert spd  == 15


# ── Boss-specific multiplikátory ──────────────────────────────────────────────

def test_boss_fortified_hp_mult():
    """Fortified Bosses is_boss=True: boss_hp_mult (1.40) > enemy_hp_mult (1.0)."""
    hp_boss,   _, _, _ = apply_modifier_to_enemy(FORTIFIED_BOSSES, 100, 20, 10, 15, is_boss=True)
    hp_normal, _, _, _ = apply_modifier_to_enemy(FORTIFIED_BOSSES, 100, 20, 10, 15, is_boss=False)
    assert hp_boss   == int(100 * 1.40)
    assert hp_normal == 100  # Fortified Bosses nemá enemy_hp_mult


def test_boss_fortified_def_mult():
    """Fortified Bosses is_boss=True: boss_def_mult (1.30)."""
    _, _, def_boss,   _ = apply_modifier_to_enemy(FORTIFIED_BOSSES, 100, 20, 10, 15, is_boss=True)
    _, _, def_normal, _ = apply_modifier_to_enemy(FORTIFIED_BOSSES, 100, 20, 10, 15, is_boss=False)
    assert def_boss   == int(10 * 1.30)
    assert def_normal == 10  # Fortified Bosses nemá enemy_def_mult


def test_boss_iron_fortress_hp_same_as_normal():
    """Iron Fortress nemá boss_hp_mult → is_boss nemá vliv na HP."""
    hp_boss,   _, _, _ = apply_modifier_to_enemy(IRON_FORTRESS, 100, 20, 10, 15, is_boss=True)
    hp_normal, _, _, _ = apply_modifier_to_enemy(IRON_FORTRESS, 100, 20, 10, 15, is_boss=False)
    assert hp_boss == hp_normal  # Oba = int(100 * 1.20)


def test_enemy_returns_integers():
    """Výsledky jsou celá čísla."""
    result = apply_modifier_to_enemy(CHAOS_WEEK, 100, 20, 10, 15)
    assert all(isinstance(v, int) for v in result)


# ══════════════════════════════════════════════════════════════════════════════
# apply_modifier_to_player
# ══════════════════════════════════════════════════════════════════════════════

def test_player_none_modifier_returns_original():
    assert apply_modifier_to_player(None, 200, 30, 15, 20) == (200, 30, 15, 20)


def test_player_ancient_blessing_hp_and_atk():
    """Ancient Blessing: +20 % HP, +10 % ATK."""
    hp, atk, def_, spd = apply_modifier_to_player(ANCIENT_BLESSING, 200, 30, 15, 20)
    assert hp  == int(200 * 1.20)
    assert atk == int(30  * 1.10)
    assert spd == 20    # SPD nikdy nemodifikováno


def test_player_chaos_week_all_stats():
    """Chaos Week: +20 % HP, ATK, DEF (SPD beze změny)."""
    hp, atk, def_, spd = apply_modifier_to_player(CHAOS_WEEK, 200, 30, 15, 20)
    assert hp   == int(200 * 1.20)
    assert atk  == int(30  * 1.20)
    assert def_ == int(15  * 1.20)
    assert spd  == 20    # SPD beze změny


def test_player_spd_never_modified():
    """SPD hráče se nikdy nemodifikuje bez ohledu na modifikátor."""
    for key, mod in DUNGEON_MODIFIERS.items():
        _, _, _, spd = apply_modifier_to_player(mod, 200, 30, 15, 42)
        assert spd == 42, f"Modifikátor '{key}' nesprávně změnil SPD hráče!"


def test_player_double_loot_no_stat_change():
    """Double Loot nemá player_XXX klíče → stats beze změny."""
    hp, atk, def_, spd = apply_modifier_to_player(DOUBLE_LOOT, 200, 30, 15, 20)
    assert (hp, atk, def_, spd) == (200, 30, 15, 20)


def test_player_returns_integers():
    """Výsledky jsou celá čísla."""
    result = apply_modifier_to_player(CHAOS_WEEK, 200, 30, 15, 20)
    assert all(isinstance(v, int) for v in result)


# ══════════════════════════════════════════════════════════════════════════════
# get_modifier_start_statuses
# ══════════════════════════════════════════════════════════════════════════════

def test_start_statuses_none_modifier():
    result = get_modifier_start_statuses(None)
    assert result == {"player": None, "enemy": None}


def test_start_status_cursed_grounds_player_poison():
    result = get_modifier_start_statuses(CURSED_GROUNDS)
    assert result["player"] == "poison"
    assert result["enemy"]  is None


def test_start_status_blessed_warriors_player_shield():
    result = get_modifier_start_statuses(BLESSED_WARRIORS)
    assert result["player"] == "shield"
    assert result["enemy"]  is None


def test_start_status_bloodmoon_player_bleed():
    result = get_modifier_start_statuses(BLOODMOON)
    assert result["player"] == "bleed"
    assert result["enemy"]  is None


def test_start_status_iron_fortress_no_statuses():
    result = get_modifier_start_statuses(IRON_FORTRESS)
    assert result["player"] is None
    assert result["enemy"]  is None


def test_start_status_double_loot_no_statuses():
    result = get_modifier_start_statuses(DOUBLE_LOOT)
    assert result["player"] is None
    assert result["enemy"]  is None


def test_start_status_always_has_player_and_enemy_keys():
    """Výsledek musí vždy obsahovat klíče 'player' a 'enemy'."""
    for key, mod in DUNGEON_MODIFIERS.items():
        result = get_modifier_start_statuses(mod)
        assert "player" in result, f"'{key}' chybí klíč 'player'"
        assert "enemy"  in result, f"'{key}' chybí klíč 'enemy'"


# ══════════════════════════════════════════════════════════════════════════════
# scale_rewards
# ══════════════════════════════════════════════════════════════════════════════

def test_scale_rewards_none_returns_original():
    xp, gold = scale_rewards(None, 100, 50)
    assert xp   == 100
    assert gold == 50


def test_scale_rewards_double_loot():
    """Double Loot: 2× XP, 2× gold."""
    xp, gold = scale_rewards(DOUBLE_LOOT, 100, 50)
    assert xp   == 200
    assert gold == 100


def test_scale_rewards_iron_fortress():
    """Iron Fortress: +25 % gold, XP beze změny."""
    xp, gold = scale_rewards(IRON_FORTRESS, 100, 100)
    assert xp   == 100
    assert gold == int(100 * 1.25)


def test_scale_rewards_berserker_rage():
    """Berserker Rage: +20 % XP, gold beze změny."""
    xp, gold = scale_rewards(BERSERKER_RAGE, 100, 100)
    assert xp   == int(100 * 1.20)
    assert gold == 100


def test_scale_rewards_fortified_bosses():
    """Fortified Bosses: +50 % XP, +50 % gold."""
    xp, gold = scale_rewards(FORTIFIED_BOSSES, 100, 100)
    assert xp   == 150
    assert gold == 150


def test_scale_rewards_no_reward_modifier():
    """Modifikátor bez reward klíčů nezmění odměny."""
    xp, gold = scale_rewards(SWIFT_PREDATORS, 200, 80)
    assert xp   == 200
    assert gold == 80


def test_scale_rewards_returns_integers():
    """Výsledky jsou celá čísla."""
    xp, gold = scale_rewards(DOUBLE_LOOT, 33, 77)
    assert isinstance(xp,   int)
    assert isinstance(gold, int)


def test_scale_rewards_zero_base():
    """Nulové vstupní hodnoty vrátí 0."""
    xp, gold = scale_rewards(DOUBLE_LOOT, 0, 0)
    assert xp   == 0
    assert gold == 0


# ══════════════════════════════════════════════════════════════════════════════
# MODIFIER_ROTATION / DUNGEON_MODIFIERS — strukturní validace
# ══════════════════════════════════════════════════════════════════════════════

def test_modifier_rotation_contains_all_keys():
    """MODIFIER_ROTATION musí obsahovat přesně všechny klíče z DUNGEON_MODIFIERS."""
    assert set(MODIFIER_ROTATION) == set(DUNGEON_MODIFIERS.keys())


def test_modifier_rotation_no_duplicates():
    """V MODIFIER_ROTATION nesmějí být duplikáty."""
    assert len(MODIFIER_ROTATION) == len(set(MODIFIER_ROTATION))


def test_all_modifiers_have_required_fields():
    """Každý modifikátor musí mít 'name', 'emoji', 'description', 'type', 'color'."""
    required = {"name", "emoji", "description", "type", "color"}
    for key, mod in DUNGEON_MODIFIERS.items():
        missing = required - set(mod.keys())
        assert not missing, f"Modifikátor '{key}' chybí klíče: {missing}"


def test_all_modifiers_name_nonempty():
    for key, mod in DUNGEON_MODIFIERS.items():
        assert mod["name"].strip(), f"Modifikátor '{key}' má prázdný name"


def test_all_modifiers_type_valid():
    """'type' musí být jeden z povolených typů."""
    valid_types = {"enemy_buff", "player_buff", "player_debuff", "mixed", "special"}
    for key, mod in DUNGEON_MODIFIERS.items():
        assert mod["type"] in valid_types, (
            f"Modifikátor '{key}' má neznámý type: '{mod['type']}'"
        )


def test_all_modifier_mult_values_positive():
    """Všechny _mult hodnoty musí být kladná čísla."""
    mult_keys = [
        "enemy_hp_mult", "enemy_atk_mult", "enemy_def_mult",
        "boss_hp_mult",  "boss_def_mult",
        "player_hp_mult","player_atk_mult","player_def_mult",
        "reward_xp_mult","reward_gold_mult",
    ]
    for key, mod in DUNGEON_MODIFIERS.items():
        for mk in mult_keys:
            if mk in mod:
                assert mod[mk] > 0, (
                    f"Modifikátor '{key}' má {mk} = {mod[mk]} (musí být > 0)"
                )
