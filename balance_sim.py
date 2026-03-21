"""
Balance simulace pro Dungeon Chronicles — všechny subclass kombinace, level 30.
Spustit z kořene projektu: python balance_sim.py
"""

import sys
import os
import io
import random
from collections import defaultdict

# Force ASCII-safe stdout pro Windows terminaly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Přidej backend do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from game.combat_engine import CombatantConfig, simulate_unified_combat
from game.combat_stats import CLASS_HP_MULT
from models.subclass import SUBCLASS_DEFINITIONS

# ── Build konfigurace ──────────────────────────────────────────────────────────
LEVEL = 30
SIMS  = 300

CLASS_BUILDS = {
    "warrior": {
        "cls": "warrior",
        "primary_stat":  60,
        "secondary_a":   30,
        "secondary_b":   20,
        "weapon_dmg":    22,
        "armor_value":   90,
        "luck":          12,
        "talents":       ["battle_rage", "fortitude"],
        "talent_t2":     "execute",
    },
    "mage": {
        "cls": "mage",
        "primary_stat":  60,
        "secondary_a":   20,
        "secondary_b":   25,
        "weapon_dmg":    18,
        "armor_value":   45,
        "luck":          15,
        "talents":       ["arcane_focus", "mana_surge"],
        "talent_t2":     "arcane_storm",
    },
    "ranger": {
        "cls": "ranger",
        "primary_stat":  60,
        "secondary_a":   25,
        "secondary_b":   20,
        "weapon_dmg":    20,
        "armor_value":   60,
        "luck":          20,
        "talents":       ["eagle_eye", "evasion"],
        "talent_t2":     "rain_of_arrows",
    },
}

# Dynamicky z models/subclass.py — vždy aktuální hodnoty
SUBCLASS_BASE_CLASS = {k: v["cls"] for k, v in SUBCLASS_DEFINITIONS.items()}
SUBCLASS_MULTS      = {k: v.get("stat_mults", {}) for k, v in SUBCLASS_DEFINITIONS.items()}

def build_config(subclass_key: str, fighter_num: int) -> CombatantConfig:
    """Sestaví CombatantConfig pro daný subclass na level 30."""
    base_cls = SUBCLASS_BASE_CLASS[subclass_key]
    build    = CLASS_BUILDS[base_cls]
    mults    = SUBCLASS_MULTS.get(subclass_key, {})

    hp_mult_class = CLASS_HP_MULT[base_cls]  # warrior=4, ranger=3, mage=3
    hp_mult_sub   = mults.get("hp_mult", 1.0)

    # HP = class_hp_mult * level * 50 * subclass_hp_mult (zjednodušená verze)
    base_hp = int(hp_mult_class * LEVEL * 50 * hp_mult_sub)

    return CombatantConfig(
        name         = f"{subclass_key.capitalize()}_{fighter_num}",
        hp           = base_hp,
        weapon_dmg   = build["weapon_dmg"],
        armor_value  = int(build["armor_value"] * mults.get("armor_mult", 1.0)),
        primary_stat = build["primary_stat"],
        secondary_a  = build["secondary_a"],
        secondary_b  = build["secondary_b"],
        luck         = build["luck"],
        level        = LEVEL,
        cls          = base_cls,
        subclass     = subclass_key,
        talents      = build["talents"],
        talent_t2    = build["talent_t2"],
        set_bonuses  = {},
    )


def run_matchup(sc_a: str, sc_b: str, n: int = SIMS) -> dict:
    """Spustí n soubojů pro daný matchup, vrátí statistiky."""
    wins_a   = 0
    wins_b   = 0
    rounds_total = 0
    timeouts     = 0

    for i in range(n):
        cfg_a = build_config(sc_a, 1)
        cfg_b = build_config(sc_b, 2)

        result = simulate_unified_combat(cfg_a, cfg_b, seed=None)

        rounds_total += result.rounds
        if result.rounds >= 30:
            timeouts += 1

        if result.attacker_won:
            wins_a += 1
        else:
            wins_b += 1

    return {
        "wins_a":  wins_a,
        "wins_b":  wins_b,
        "pct_a":   wins_a / n * 100,
        "pct_b":   wins_b / n * 100,
        "avg_rounds": rounds_total / n,
        "timeout_pct": timeouts / n * 100,
    }


def main():
    subclasses = ["berserker", "guardian", "elementalist", "necromancer", "sharpshooter", "shadowblade"]
    n = len(subclasses)

    print(f"\n{'='*72}")
    print(f" Dungeon Chronicles — Balance Simulace  |  Level {LEVEL}  |  {SIMS} soubojů/matchup")
    print(f"{'='*72}\n")

    # Zobraz build parametry
    print("BUILD PARAMETRY:")
    for sc in subclasses:
        base_cls = SUBCLASS_BASE_CLASS[sc]
        build = CLASS_BUILDS[base_cls]
        mults = SUBCLASS_MULTS.get(sc, {})
        hp = int(CLASS_HP_MULT[base_cls] * LEVEL * 50 * mults.get("hp_mult", 1.0))
        arm = int(build["armor_value"] * mults.get("armor_mult", 1.0))
        print(f"  {sc:<14} ({base_cls:<8})  HP={hp:>5}  ARM={arm:>3}  T2={build['talent_t2']}")

    print()

    # Výsledná matice: results[a][b] = win% a vs b
    results = {}
    for sc_a in subclasses:
        results[sc_a] = {}
        for sc_b in subclasses:
            if sc_a == sc_b:
                results[sc_a][sc_b] = None
                continue
            # Spustit pouze jednou — výsledek druhé strany je 100 - pct_a
            if sc_b in results and sc_a in results[sc_b] and results[sc_b][sc_a] is not None:
                inv = results[sc_b][sc_a]
                results[sc_a][sc_b] = {
                    "wins_a": inv["wins_b"], "wins_b": inv["wins_a"],
                    "pct_a": inv["pct_b"], "pct_b": inv["pct_a"],
                    "avg_rounds": inv["avg_rounds"],
                    "timeout_pct": inv["timeout_pct"],
                }
                continue
            print(f"  Simuluji {sc_a} vs {sc_b}...", end="", flush=True)
            stats = run_matchup(sc_a, sc_b)
            results[sc_a][sc_b] = stats
            print(f"  {stats['pct_a']:.1f}% / {stats['pct_b']:.1f}%  (avg {stats['avg_rounds']:.1f}r, {stats['timeout_pct']:.0f}% TO)")

    # ── WIN% MATICE ────────────────────────────────────────────────────────────
    col_w = 13
    header = f"{'Attacker ->':<14}" + "".join(f"{sc[:col_w]:>{col_w}}" for sc in subclasses)
    sep    = "-" * len(header)

    print(f"\n{'='*72}")
    print(" WIN% MATICE  (radek = utocnik, sloupec = obrance)")
    print(f"{'='*72}")
    print(header)
    print(sep)

    for sc_a in subclasses:
        row = f"{sc_a:<14}"
        for sc_b in subclasses:
            if sc_a == sc_b:
                row += f"{'---':>{col_w}}"
            else:
                pct = results[sc_a][sc_b]["pct_a"]
                # Barevné kódování textové
                if pct >= 65:
                    marker = "**"
                elif pct >= 55:
                    marker = " +"
                elif pct <= 35:
                    marker = " -"
                elif pct <= 45:
                    marker = "  "
                else:
                    marker = "  "
                row += f"{f'{pct:.1f}%{marker}':>{col_w}}"
        print(row)

    print(sep)
    print("  ** = dominantní (≥65%) | + = výhoda (55-64%) | - = nevýhoda (≤45%)")

    # ── CELKOVÉ WIN% (průměr přes všechny matchupy) ───────────────────────────
    print(f"\n{'='*72}")
    print(" CELKOVÝ WIN% (průměr vs všech ostatních subclassů)")
    print(f"{'='*72}")

    overall = {}
    for sc_a in subclasses:
        wins_list = []
        for sc_b in subclasses:
            if sc_a == sc_b:
                continue
            wins_list.append(results[sc_a][sc_b]["pct_a"])
        overall[sc_a] = sum(wins_list) / len(wins_list)

    sorted_overall = sorted(overall.items(), key=lambda x: -x[1])
    for rank, (sc, pct) in enumerate(sorted_overall, 1):
        bar = "#" * int(pct / 2)
        print(f"  {rank}. {sc:<14}  {pct:5.1f}%  {bar}")

    # ── DETAILNÍ STATISTIKY ────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(" DETAILNÍ STATISTIKY (průměrná délka + timeout %)")
    print(f"{'='*72}")
    print(f"  {'Matchup':<32}  {'Win%':>6}  {'Avg Rounds':>10}  {'Timeout%':>9}")
    print(f"  {'-'*32}  {'-'*6}  {'-'*10}  {'-'*9}")

    # Zajímavé matchupy — seřazené podle win% (nejextrémnější první)
    matchup_list = []
    for sc_a in subclasses:
        for sc_b in subclasses:
            if sc_a >= sc_b:
                continue
            r = results[sc_a][sc_b]
            matchup_list.append((sc_a, sc_b, r["pct_a"], r["avg_rounds"], r["timeout_pct"]))

    matchup_list.sort(key=lambda x: abs(x[2] - 50), reverse=True)

    for sc_a, sc_b, pct_a, avg_r, to_pct in matchup_list:
        pct_b = 100 - pct_a
        balance = "IMBAL" if abs(pct_a - 50) >= 20 else ("SKEWED" if abs(pct_a - 50) >= 10 else "OK")
        print(f"  {sc_a:<14} vs {sc_b:<14}  {pct_a:5.1f}%  {avg_r:>10.1f}  {to_pct:>8.0f}%  {balance}")

    # ── BALANCE VAROVÁNÍ ──────────────────────────────────────────────────────
    print(f"\n{'='*72}")
    print(" BALANCE VAROVÁNÍ")
    print(f"{'='*72}")
    issues = []
    for sc_a in subclasses:
        for sc_b in subclasses:
            if sc_a == sc_b:
                continue
            pct = results[sc_a][sc_b]["pct_a"]
            if pct >= 70:
                issues.append(f"  KRITICKY OP: {sc_a} vs {sc_b} = {pct:.1f}%")
            elif pct >= 60:
                issues.append(f"  MÍRNĚ OP:    {sc_a} vs {sc_b} = {pct:.1f}%")

    if issues:
        # Deduplikace
        seen = set()
        for iss in issues:
            key = iss.strip()
            if key not in seen:
                seen.add(key)
                print(iss)
    else:
        print("  Žádná kritická nerovnováha detekována.")

    print(f"\n{'='*72}\n")


if __name__ == "__main__":
    main()
