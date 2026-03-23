"""
Balance simulace pro Dungeon Chronicles — PvP + PvE (dungeon stages), level 30.
Spustit z kořene projektu: python balance_sim.py

Buildy jsou automaticky odvozeny z reálných herních dat (SEED_ITEMS, SEED_CLASS_ITEMS)
přes game/sim_builds.py — změny itemů v seed.py se automaticky projeví.
"""

import sys
import os
import io

# Force ASCII-safe stdout pro Windows terminaly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Přidej backend do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from game.combat_engine import CombatantConfig, simulate_unified_combat
from game.combat_stats import CLASS_HP_MULT
from game.sim_builds import get_benchmark_build, get_best_gear
from models.subclass import SUBCLASS_DEFINITIONS
from models.dungeon_run import DUNGEON_DEFINITIONS

# ── Konfigurace ────────────────────────────────────────────────────────────────
LEVEL    = 30
SIMS     = 300
# Tier vybavení pro benchmark: "common" | "uncommon" | "rare" | "epic" | "legendary"
GEAR_TIER = "epic"

# ── Talenty (design choices — nezávislé na itemech) ───────────────────────────
CLASS_TALENTS: dict[str, dict] = {
    "warrior": {"talents": ["battle_rage", "fortitude", "iron_skin"], "talent_t2": "execute"},
    "mage":    {"talents": ["arcane_focus", "mana_surge", "spell_echo"],  "talent_t2": "arcane_storm"},
    "ranger":  {"talents": ["eagle_eye", "evasion", "hunters_mark"],      "talent_t2": "rain_of_arrows"},
}

# ── Benchmark builds (odvozeno z herních dat při startu) ──────────────────────
_BENCHMARK: dict[str, dict] = {
    cls: get_benchmark_build(cls, level=LEVEL, max_rarity=GEAR_TIER)
    for cls in ("warrior", "mage", "ranger")
}

# Subclass lookup z models/subclass.py
SUBCLASS_BASE_CLASS = {k: v["cls"] for k, v in SUBCLASS_DEFINITIONS.items()}
SUBCLASS_MULTS      = {k: v.get("stat_mults", {}) for k, v in SUBCLASS_DEFINITIONS.items()}

SUBCLASSES = ["berserker", "guardian", "elementalist", "necromancer", "sharpshooter", "shadowblade"]


# ── Build helpers ──────────────────────────────────────────────────────────────

def build_config(subclass_key: str, fighter_num: int) -> CombatantConfig:
    """Sestaví CombatantConfig pro daný subclass na level LEVEL."""
    base_cls = SUBCLASS_BASE_CLASS[subclass_key]
    bench    = _BENCHMARK[base_cls]
    talents  = CLASS_TALENTS[base_cls]
    mults    = SUBCLASS_MULTS.get(subclass_key, {})

    hp_mult_class = CLASS_HP_MULT[base_cls]
    hp_mult_sub   = mults.get("hp_mult", 1.0)
    base_hp = int(hp_mult_class * LEVEL * 50 * hp_mult_sub)

    return CombatantConfig(
        name         = f"{subclass_key.capitalize()}_{fighter_num}",
        hp           = base_hp,
        weapon_dmg   = bench["weapon_dmg"],
        armor_value  = int(bench["armor_value"] * mults.get("armor_mult", 1.0)),
        primary_stat = bench["primary_stat"],
        secondary_a  = bench["secondary_a"],
        secondary_b  = bench["secondary_b"],
        luck         = bench["luck"],
        level        = LEVEL,
        cls          = base_cls,
        subclass     = subclass_key,
        talents      = talents["talents"],
        talent_t2    = talents["talent_t2"],
        set_bonuses  = {},
    )


def build_dungeon_enemy(stage_def: dict) -> CombatantConfig:
    """Sestaví CombatantConfig pro dungeon nepřítele podle stage_def."""
    mult    = stage_def["enemy_mult"]
    is_boss = stage_def["type"] == "boss"

    hp          = int(60 * LEVEL * mult)
    weapon_dmg  = int(9  * LEVEL * mult)
    armor_value = int(5  * LEVEL * mult)

    return CombatantConfig(
        name              = stage_def["enemy_name"],
        hp                = hp,
        weapon_dmg        = weapon_dmg,
        armor_value       = armor_value,
        primary_stat      = 0,
        secondary_a       = 0,
        secondary_b       = 0,
        luck              = 5,
        level             = LEVEL,
        cls               = "warrior",
        subclass          = "",
        talents           = [],
        talent_t2         = "",
        set_bonuses       = {},
        is_boss           = is_boss,
        phases            = stage_def.get("phases", []),
        special_abilities = stage_def.get("special_abilities", []),
    )


# ── Simulační funkce ───────────────────────────────────────────────────────────

def run_pvp_matchup(sc_a: str, sc_b: str, n: int = SIMS) -> dict:
    """Spustí n PvP soubojů, vrátí statistiky."""
    wins_a = wins_b = rounds_total = timeouts = 0

    for _ in range(n):
        result = simulate_unified_combat(build_config(sc_a, 1), build_config(sc_b, 2), seed=None)
        rounds_total += result.rounds
        if result.rounds >= 30:
            timeouts += 1
        if result.attacker_won:
            wins_a += 1
        else:
            wins_b += 1

    return {
        "wins_a": wins_a, "wins_b": wins_b,
        "pct_a":  wins_a / n * 100, "pct_b": wins_b / n * 100,
        "avg_rounds": rounds_total / n,
        "timeout_pct": timeouts / n * 100,
    }


def run_pve_matchup(sc: str, stage_def: dict, n: int = SIMS) -> dict:
    """Spustí n PvE soubojů hráče vs dungeon stage, vrátí statistiky."""
    wins = rounds_total = timeouts = 0

    for _ in range(n):
        result = simulate_unified_combat(build_config(sc, 1), build_dungeon_enemy(stage_def), seed=None)
        rounds_total += result.rounds
        if result.rounds >= 30:
            timeouts += 1
        if result.attacker_won:
            wins += 1

    return {
        "wins": wins,
        "pct":  wins / n * 100,
        "avg_rounds": rounds_total / n,
        "timeout_pct": timeouts / n * 100,
    }


# ── Výstupní sekce ─────────────────────────────────────────────────────────────

def print_build_params():
    print(f"BUILD PARAMETRY  (gear tier: {GEAR_TIER}, level {LEVEL})")
    print()

    # Gear breakdown per class
    for cls in ("warrior", "mage", "ranger"):
        bench = _BENCHMARK[cls]
        gear  = get_best_gear(cls, max_level=LEVEL, max_rarity=GEAR_TIER)
        print(f"  {cls.upper()}  weapon_dmg={bench['weapon_dmg']}  armor={bench['armor_value']}"
              f"  primary={bench['primary_stat']}  sec_a={bench['secondary_a']}"
              f"  sec_b={bench['secondary_b']}  luck={bench['luck']}")
        for slot, item in gear["selected_items"].items():
            print(f"    {slot:<8} {item}")
        print()

    # Subclass přehled s vypočtenými HP a armor
    print("SUBCLASS PŘEHLED (HP + armor po subclass multech):")
    for sc in SUBCLASSES:
        base_cls = SUBCLASS_BASE_CLASS[sc]
        bench    = _BENCHMARK[base_cls]
        talents  = CLASS_TALENTS[base_cls]
        mults    = SUBCLASS_MULTS.get(sc, {})
        hp  = int(CLASS_HP_MULT[base_cls] * LEVEL * 50 * mults.get("hp_mult", 1.0))
        arm = int(bench["armor_value"] * mults.get("armor_mult", 1.0))
        t1  = ", ".join(talents["talents"])
        print(f"  {sc:<14} ({base_cls:<8})  HP={hp:>5}  ARM={arm:>3}  [{t1}]  T2={talents['talent_t2']}")
    print()


def print_pvp_section():
    print(f"\n{'='*76}")
    print(f" PvP SIMULACE  |  Level {LEVEL}  |  {SIMS} soubojů/matchup")
    print(f"{'='*76}")

    # Výpočet matice
    results = {}
    for sc_a in SUBCLASSES:
        results[sc_a] = {}
        for sc_b in SUBCLASSES:
            if sc_a == sc_b:
                results[sc_a][sc_b] = None
                continue
            if sc_b in results and sc_a in results[sc_b] and results[sc_b][sc_a] is not None:
                inv = results[sc_b][sc_a]
                results[sc_a][sc_b] = {
                    "wins_a": inv["wins_b"], "wins_b": inv["wins_a"],
                    "pct_a": inv["pct_b"],  "pct_b":  inv["pct_a"],
                    "avg_rounds": inv["avg_rounds"],
                    "timeout_pct": inv["timeout_pct"],
                }
                continue
            print(f"  Simuluji {sc_a} vs {sc_b}...", end="", flush=True)
            stats = run_pvp_matchup(sc_a, sc_b)
            results[sc_a][sc_b] = stats
            print(f"  {stats['pct_a']:.1f}% / {stats['pct_b']:.1f}%  (avg {stats['avg_rounds']:.1f}r, {stats['timeout_pct']:.0f}% TO)")

    # WIN% matice
    col_w  = 13
    header = f"{'Attacker ->':<14}" + "".join(f"{sc[:col_w]:>{col_w}}" for sc in SUBCLASSES)
    sep    = "-" * len(header)

    print(f"\n WIN% MATICE  (radek = utocnik, sloupec = obrance)")
    print(header)
    print(sep)

    for sc_a in SUBCLASSES:
        row = f"{sc_a:<14}"
        for sc_b in SUBCLASSES:
            if sc_a == sc_b:
                row += f"{'---':>{col_w}}"
            else:
                pct = results[sc_a][sc_b]["pct_a"]
                marker = "**" if pct >= 65 else (" +" if pct >= 55 else (" -" if pct <= 45 else "  "))
                row += f"{f'{pct:.1f}%{marker}':>{col_w}}"
        print(row)

    print(sep)
    print("  ** = dominantní (≥65%) | + = výhoda (55-64%) | - = nevýhoda (≤45%)")

    # Celkový žebříček
    print(f"\n CELKOVÝ WIN% (průměr vs všech ostatních)")
    overall = {}
    for sc_a in SUBCLASSES:
        pcts = [results[sc_a][sc_b]["pct_a"] for sc_b in SUBCLASSES if sc_b != sc_a]
        overall[sc_a] = sum(pcts) / len(pcts)

    for rank, (sc, pct) in enumerate(sorted(overall.items(), key=lambda x: -x[1]), 1):
        bar = "#" * int(pct / 2)
        print(f"  {rank}. {sc:<14}  {pct:5.1f}%  {bar}")

    # Balance varování
    print(f"\n BALANCE VAROVÁNÍ (PvP):")
    issues = []
    seen = set()
    for sc_a in SUBCLASSES:
        for sc_b in SUBCLASSES:
            if sc_a == sc_b:
                continue
            pct = results[sc_a][sc_b]["pct_a"]
            if pct >= 70:
                tag = f"  KRITICKY OP: {sc_a} vs {sc_b} = {pct:.1f}%"
            elif pct >= 60:
                tag = f"  MIRNE OP:    {sc_a} vs {sc_b} = {pct:.1f}%"
            else:
                continue
            key = tag.strip()
            if key not in seen:
                seen.add(key)
                issues.append(tag)

    if issues:
        for iss in issues:
            print(iss)
    else:
        print("  Zadna kriticka nerovnovaha detekována.")

    return results


def print_pve_section():
    print(f"\n{'='*76}")
    print(f" PvE SIMULACE — DUNGEONY  |  Level {LEVEL}  |  {SIMS} soubojů/stage")
    print(f"{'='*76}")

    dungeon_order = ["tomb_of_forgotten", "fiery_depths", "citadel_of_chaos"]

    # Výpočet všech výsledků
    all_results = {}
    for dkey in dungeon_order:
        ddef = DUNGEON_DEFINITIONS[dkey]
        all_results[dkey] = {}
        for stage in ddef["stages"]:
            snum = stage["stage_num"]
            is_boss = stage["type"] == "boss"
            tag = f"[BOSS]" if is_boss else (f"[mini]" if stage["type"] == "miniboss" else "      ")
            print(f"\n  {ddef['name']}  Stage {snum} {tag} — {stage['enemy_name']} (mult {stage['enemy_mult']:.2f})")
            all_results[dkey][snum] = {}
            for sc in SUBCLASSES:
                stats = run_pve_matchup(sc, stage)
                all_results[dkey][snum][sc] = stats
                bar = "#" * int(stats["pct"] / 5)
                print(f"    {sc:<14}  {stats['pct']:5.1f}%  {bar}")

    # Souhrnné tabulky
    print(f"\n{'='*76}")
    print(" SOUHRN: WIN% PER SUBCLASS PER STAGE")
    print(f"{'='*76}")

    for dkey in dungeon_order:
        ddef   = DUNGEON_DEFINITIONS[dkey]
        stages = ddef["stages"]
        print(f"\n  {ddef['emoji']}  {ddef['name'].upper()}  (min level {ddef['min_level']})")

        col_w = 10
        header = f"  {'Subclass':<14}" + "".join(
            f"  {'S'+str(s['stage_num'])+'('+s['type'][:1].upper()+')':>{col_w}}"
            for s in stages
        ) + f"  {'Avg':>{col_w}}"
        print(header)
        print("  " + "-" * (len(header) - 2))

        for sc in SUBCLASSES:
            row  = f"  {sc:<14}"
            pcts = []
            for s in stages:
                pct = all_results[dkey][s["stage_num"]][sc]["pct"]
                pcts.append(pct)
                marker = "!" if pct < 30 else ("+" if pct >= 70 else " ")
                row += f"  {f'{pct:.0f}%{marker}':>{col_w}}"
            avg = sum(pcts) / len(pcts)
            row += f"  {f'{avg:.0f}%':>{col_w}}"
            print(row)

        print(f"  Legenda: + = snazy (≥70%) | ! = tezky (≤30%)")

    # Boss-only highlight
    print(f"\n{'='*76}")
    print(" BOSS WIN% PREHLED (stage 5 kazdeho dungeonu)")
    print(f"{'='*76}")
    print(f"  {'Subclass':<14}" + "".join(f"  {DUNGEON_DEFINITIONS[d]['name'][:18]:>20}" for d in dungeon_order))
    print("  " + "-" * 80)
    for sc in SUBCLASSES:
        row = f"  {sc:<14}"
        for dkey in dungeon_order:
            pct = all_results[dkey][5][sc]["pct"]
            marker = "!" if pct < 20 else ("*" if pct >= 60 else " ")
            row += f"  {f'{pct:.0f}%{marker}':>20}"
        print(row)
    print("  Legenda: * = zdrave (≥60%) | ! = kriticky tezke (≤20%)")

    # PvE balance varování
    print(f"\n BALANCE VAROVÁNÍ (PvE):")
    boss_issues = []
    for dkey in dungeon_order:
        dname = DUNGEON_DEFINITIONS[dkey]["name"]
        for sc in SUBCLASSES:
            pct = all_results[dkey][5][sc]["pct"]
            if pct < 15:
                boss_issues.append(f"  NEPRUCHOZI BOSS: {sc} vs {dname} boss = {pct:.0f}%")
            elif pct < 30:
                boss_issues.append(f"  TEZKY BOSS:      {sc} vs {dname} boss = {pct:.0f}%")

    if boss_issues:
        for iss in boss_issues:
            print(iss)
    else:
        print("  Vsechny subclassy maji ≥30% sanci na bossich.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*76}")
    print(f" Dungeon Chronicles — Balance Simulace  |  Level {LEVEL}  |  {SIMS} souboju/matchup")
    print(f"{'='*76}\n")

    print_build_params()
    print_pvp_section()
    print_pve_section()

    print(f"\n{'='*76}\n")


if __name__ == "__main__":
    main()
