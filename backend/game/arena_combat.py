"""
game/arena_combat.py — PvP aréna combat engine s ELO systémem
"""
import random
from dataclasses import dataclass


# ── ELO systém ────────────────────────────────────────────────────────────────
ELO_K = 32          # K-faktor (jak rychle se ELO mění)
ELO_MIN = 100       # Minimum ELO
ELO_WIN_BASE = 15   # Základní ELO za výhru
ELO_LOSS_BASE = -10 # Základní ELO za prohru

def calc_elo_change(attacker_elo: int, defender_elo: int, attacker_won: bool) -> tuple[int, int]:
    """Vrátí (attacker_elo_change, defender_elo_change)."""
    # Očekávaný výsledek podle ELO
    expected_a = 1 / (1 + 10 ** ((defender_elo - attacker_elo) / 400))
    expected_d = 1 - expected_a

    actual_a = 1.0 if attacker_won else 0.0
    actual_d = 1.0 - actual_a

    change_a = int(ELO_K * (actual_a - expected_a))
    change_d = int(ELO_K * (actual_d - expected_d))

    # Minimální ELO change ±3
    change_a = max(3, change_a) if attacker_won else min(-3, change_a)
    change_d = max(3, change_d) if not attacker_won else min(-3, change_d)

    return change_a, change_d


# ── PvP souboj ────────────────────────────────────────────────────────────────
@dataclass
class Fighter:
    name: str
    hp: int
    atk: int
    defense: int
    spd: int
    luck: int
    level: int


def pvp_fight(attacker: Fighter, defender: Fighter) -> dict:
    """
    Simuluje PvP souboj. Vrátí výsledek s battle logem.
    """
    log = []
    log.append(f"⚔ {attacker.name} (Lv.{attacker.level}) vs {defender.name} (Lv.{defender.level})")
    log.append("─" * 48)

    hp_a = attacker.hp
    hp_d = defender.hp
    max_rounds = 20
    round_num = 0

    # Kdo útočí první — vyšší SPD začíná
    if attacker.spd >= defender.spd:
        first, second = attacker, defender
        first_is_attacker = True
    else:
        first, second = defender, attacker
        first_is_attacker = False

    while hp_a > 0 and hp_d > 0 and round_num < max_rounds:
        round_num += 1
        log.append(f"[Kolo {round_num}] HP: {attacker.name}={hp_a} | {defender.name}={hp_d}")

        # Útok prvního na druhého
        for atk_fighter, def_fighter, is_atk_side in [
            (first, second, first_is_attacker),
            (second, first, not first_is_attacker),
        ]:
            if hp_a <= 0 or hp_d <= 0:
                break

            is_crit = random.random() < (atk_fighter.luck / 200)
            dodge   = random.random() < (def_fighter.spd / 300)

            if dodge:
                log.append(f"  💨 {def_fighter.name} uhýbá útoku!")
                continue

            raw_dmg = atk_fighter.atk + random.randint(-3, 5)
            dmg = max(1, raw_dmg - def_fighter.defense // 2)

            if is_crit:
                dmg = int(dmg * 1.8)
                log.append(f"  💥 KRITICKÝ ZÁSAH! {atk_fighter.name} zasahuje za {dmg} dmg!")
            else:
                log.append(f"  🗡 {atk_fighter.name} zasahuje za {dmg} dmg")

            if is_atk_side:
                hp_d -= dmg
            else:
                hp_a -= dmg

    log.append("─" * 48)

    # Výsledek
    if hp_a > 0 and hp_d <= 0:
        winner_name = attacker.name
        attacker_won = True
        log.append(f"🏆 {attacker.name} zvítězil v aréně!")
    elif hp_d > 0 and hp_a <= 0:
        winner_name = defender.name
        attacker_won = False
        log.append(f"🏆 {defender.name} zvítězil v aréně!")
    else:
        # Remíza — kdo má více HP
        if hp_a >= hp_d:
            winner_name = attacker.name
            attacker_won = True
            log.append(f"⚖ Čas vypršel — {attacker.name} přežil s více HP!")
        else:
            winner_name = defender.name
            attacker_won = False
            log.append(f"⚖ Čas vypršel — {defender.name} přežil s více HP!")

    return {
        "winner_name": winner_name,
        "attacker_won": attacker_won,
        "attacker_hp_remaining": max(0, hp_a),
        "defender_hp_remaining": max(0, hp_d),
        "rounds": round_num,
        "battle_log": log,
    }
