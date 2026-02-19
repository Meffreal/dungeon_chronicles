"""
game/combat.py — Bojová logika pro questy i arénu

Boj je deterministický výpočet (žádný live input od hráče).
Výsledek závisí na stats, ale obsahuje kontrolovanou náhodu.
"""
import random
import math
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CombatStats:
    name:   str
    hp:     int
    atk:    int
    def_:   int
    spd:    int
    luck:   int = 5
    level:  int = 1

@dataclass
class CombatResult:
    winner:      str           # "player" nebo "enemy"
    rounds:      int
    log:         list[str]     # textový popis každého kola
    player_hp_remaining: int
    xp_gained:   int = 0
    gold_gained: int = 0

def _crit_chance(luck: int) -> float:
    """Šance na kritický zásah (0.05 – 0.35)."""
    return min(0.35, 0.05 + luck * 0.01)

def _dodge_chance(spd: int, attacker_spd: int) -> float:
    """Šance na uhnutí — závisí na rozdílu rychlostí."""
    diff = spd - attacker_spd
    return max(0.03, min(0.35, 0.10 + diff * 0.015))

def _calc_damage(atk: int, def_: int, crit: bool = False) -> int:
    """Vypočítá poškození s rozptylem ±15%."""
    base = max(1, atk - def_ // 2)
    variance = random.uniform(0.85, 1.15)
    dmg = int(base * variance)
    if crit:
        dmg = int(dmg * 1.75)
    return max(1, dmg)

def simulate_combat(player: CombatStats, enemy: CombatStats,
                    max_rounds: int = 30) -> CombatResult:
    """
    Simuluje plný souboj kolo po kole.
    Vrátí CombatResult s výsledkem a log textem.
    """
    log = []
    php = player.hp
    ehp = enemy.hp
    round_num = 0

    # Kdo jde první — vyšší SPD
    player_first = player.spd >= enemy.spd

    log.append(f"⚔️  {player.name} (Lv.{player.level}) vs {enemy.name} (Lv.{enemy.level})")
    log.append(f"📊  HP: {php} | ATK: {player.atk} | DEF: {player.def_} | SPD: {player.spd}")
    log.append("─" * 40)

    def attack(attacker: CombatStats, defender_hp: int, defender: CombatStats,
                a_name: str, d_name: str) -> tuple[int, str]:
        """Jeden útok. Vrátí (nové HP obránce, log text)."""
        # Dodge check
        if random.random() < _dodge_chance(defender.spd, attacker.spd):
            return defender_hp, f"  💨 {d_name} uhnul útoku!"

        # Crit check
        is_crit = random.random() < _crit_chance(attacker.luck)
        dmg = _calc_damage(attacker.atk, defender.def_, is_crit)
        new_hp = max(0, defender_hp - dmg)

        crit_txt = " 💥 KRITICKÝ ZÁSAH!" if is_crit else ""
        txt = f"  ⚔️  {a_name} útočí → {dmg} dmg{crit_txt}  [{d_name} HP: {new_hp}]"
        return new_hp, txt

    for round_num in range(1, max_rounds + 1):
        log.append(f"\n[Kolo {round_num}]")

        if player_first:
            ehp, txt = attack(player, ehp, enemy, player.name, enemy.name)
            log.append(txt)
            if ehp <= 0:
                break
            php, txt = attack(enemy, php, player, enemy.name, player.name)
            log.append(txt)
            if php <= 0:
                break
        else:
            php, txt = attack(enemy, php, player, enemy.name, player.name)
            log.append(txt)
            if php <= 0:
                break
            ehp, txt = attack(player, ehp, enemy, player.name, enemy.name)
            log.append(txt)
            if ehp <= 0:
                break

    # Výsledek
    if ehp <= 0:
        winner = "player"
        log.append(f"\n🏆 {player.name} zvítězil po {round_num} kolech!")
    elif php <= 0:
        winner = "enemy"
        log.append(f"\n💀 {player.name} byl poražen v kole {round_num}.")
    else:
        # Timeout — kdo má víc HP % vyhrává
        winner = "player" if (php / player.hp) >= (ehp / enemy.hp) else "enemy"
        log.append(f"\n⏰ Čas vypršel! Vítěz: {'hráč' if winner == 'player' else 'nepřítel'}.")

    return CombatResult(
        winner=winner,
        rounds=round_num,
        log=log,
        player_hp_remaining=max(0, php),
    )

def quest_enemy_stats(quest_def: tuple, character_level: int) -> CombatStats:
    """
    Generuje stats nepřítele pro daný quest a level hráče.
    quest_def = (id, name, desc, difficulty, duration_min, xp, gold_min, gold_max, min_level, icon)
    """
    difficulty = quest_def[3]
    base_level = max(quest_def[8], character_level)  # min_level nebo char level

    mult = {"easy": 0.75, "normal": 1.0, "hard": 1.35, "boss": 2.0}.get(difficulty, 1.0)

    return CombatStats(
        name=f"[{quest_def[1]}] Nepřítel",
        hp=int(50 * base_level * mult),
        atk=int(8  * base_level * mult),
        def_=int(4 * base_level * mult),
        spd=int(6  * base_level * mult * 0.8),
        luck=int(3 * mult),
        level=base_level,
    )

def calculate_win_chance(player: CombatStats, enemy: CombatStats) -> float:
    """
    Rychlý odhad šance na výhru (0.0–1.0) bez simulace.
    Používá se pro zobrazení v UI.
    """
    p_power = player.hp * 0.4 + player.atk * 2.5 + player.def_ * 1.5 + player.spd * 0.5
    e_power = enemy.hp  * 0.4 + enemy.atk  * 2.5 + enemy.def_  * 1.5 + enemy.spd  * 0.5
    ratio = p_power / max(1, p_power + e_power)
    return round(min(0.97, max(0.03, ratio)), 2)
