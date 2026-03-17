"""
game/talents.py — Talent Tree Tier 1: pasivní traity per class.

Odemykání: automaticky na level 10, 20, 30.
Efekty jsou pasivní — aplikovány při každém souboji v _FighterState.

Warrior : Odolnost (10) · Válečná Zuřivost (20) · Železná Kůže (30)
Mage    : Arkánné Soustředění (10) · Příval Many (20) · Ozvěna Kouzla (30)
Ranger  : Orlí Zrak (10) · Úskok (20) · Lovecká Značka (30)
"""

TALENT_TREE: dict = {
    # ── Warrior ──────────────────────────────────────────────────────────────
    "fortitude": {
        "class": "warrior", "level_req": 10,
        "name": "Odolnost", "emoji": "🧱",
        "desc": "+15 % maximálního HP.",
        "effect": {"hp_pct": 0.15},
    },
    "battle_rage": {
        "class": "warrior", "level_req": 20,
        "name": "Válečná Zuřivost", "emoji": "😤",
        "desc": "+25 % poškození při kritickém zásahu.",
        "effect": {"crit_dmg_bonus_pct": 0.25},
    },
    "iron_skin": {
        "class": "warrior", "level_req": 30,
        "name": "Železná Kůže", "emoji": "🛡️",
        "desc": "-20 % přijatého fyzického poškození.",
        "effect": {"dmg_reduction_pct": 0.20},
    },
    # ── Mage ─────────────────────────────────────────────────────────────────
    "arcane_focus": {
        "class": "mage", "level_req": 10,
        "name": "Arkánné Soustředění", "emoji": "🔮",
        "desc": "+20 % poškození speciálních schopností.",
        "effect": {"ability_dmg_pct": 0.20},
    },
    "mana_surge": {
        "class": "mage", "level_req": 20,
        "name": "Příval Many", "emoji": "💧",
        "desc": "+15 % poškození.",
        "effect": {"dmg_bonus_pct": 0.15},
    },
    "spell_echo": {
        "class": "mage", "level_req": 30,
        "name": "Ozvěna Kouzla", "emoji": "✨",
        "desc": "25 % šance zopakovat speciální schopnost za 60 % poškození.",
        "effect": {"echo_chance": 0.25, "echo_dmg_pct": 0.60},
    },
    # ── Ranger ───────────────────────────────────────────────────────────────
    "eagle_eye": {
        "class": "ranger", "level_req": 10,
        "name": "Orlí Zrak", "emoji": "🦅",
        "desc": "+8 LUCK (vyšší šance na kritický zásah).",
        "effect": {"luck_bonus": 8},
    },
    "evasion": {
        "class": "ranger", "level_req": 20,
        "name": "Úskok", "emoji": "💨",
        "desc": "+10 % šance na kritický zásah.",
        "effect": {"crit_bonus_pct": 0.10},
    },
    "hunters_mark": {
        "class": "ranger", "level_req": 30,
        "name": "Lovecká Značka", "emoji": "🎯",
        "desc": "První útok v souboji způsobí +50 % poškození.",
        "effect": {"first_strike_bonus_pct": 0.50},
    },
}


def get_class_talents(cls: str) -> list[dict]:
    """Vrátí talenty pro danou třídu, seřazené podle level_req."""
    return sorted(
        [{"key": k, **v} for k, v in TALENT_TREE.items() if v["class"] == cls],
        key=lambda t: t["level_req"],
    )


def get_unlockable_keys(cls: str, level: int) -> list[str]:
    """Vrátí klíče talentů splňujících level_req pro danou třídu a level."""
    return [k for k, v in TALENT_TREE.items()
            if v["class"] == cls and v["level_req"] <= level]


# ── Talent Tree Tier 2 — aktivní schopnosti (irreverzibilní volba na levelu 25) ─
TALENT_T2_TREE: dict = {
    "warrior": [
        {
            "key": "cyclone_strike",
            "name": "Cyklónový Úder",
            "emoji": "🌪",
            "level_req": 25,
            "desc": "Každé 4. kolo: 3 rychlé údery po 50% ATK. Celkem 1.5× ATK.",
            "effect": {"hits": 3, "dmg_pct_each": 0.50},
        },
        {
            "key": "rallying_cry",
            "name": "Bojový Pokřik",
            "emoji": "📯",
            "level_req": 25,
            "desc": "Každé 4. kolo: obnova 15% max HP + aktivuje štít (blokuje 20% dmg 2 kola).",
            "effect": {"heal_pct": 0.15, "shield_pct": 0.20, "shield_rounds": 2},
        },
        {
            "key": "execute",
            "name": "Poprava",
            "emoji": "⚰",
            "level_req": 25,
            "desc": "Každé 4. kolo: pokud má nepřítel méně než 25% HP, útok způsobí 3× ATK.",
            "effect": {"threshold_pct": 0.25, "dmg_mult": 3.0, "normal_mult": 1.0},
        },
    ],
    "mage": [
        {
            "key": "arcane_storm",
            "name": "Arkánná Bouře",
            "emoji": "⚡",
            "level_req": 25,
            "desc": "Každé 4. kolo: 3 kouzla po 60% ability dmg, ignorují brnění.",
            "effect": {"hits": 3, "dmg_pct_each": 0.60, "piercing": True},
        },
        {
            "key": "mana_void",
            "name": "Prázdnota Many",
            "emoji": "🕳",
            "level_req": 25,
            "desc": "Každé 4. kolo: aplikuje Oslabení na nepřítele (2 kola).",
            "effect": {"apply_status": "weaken", "rounds": 2},
        },
        {
            "key": "time_warp",
            "name": "Časový Zlom",
            "emoji": "⏳",
            "level_req": 25,
            "desc": "Každé 4. kolo: okamžitý druhý útok schopností za 80% dmg.",
            "effect": {"extra_ability_pct": 0.80},
        },
    ],
    "ranger": [
        {
            "key": "rain_of_arrows",
            "name": "Déšť Šípů",
            "emoji": "🏹",
            "level_req": 25,
            "desc": "Každé 4. kolo: 4 šípy po 40% ATK + aplikuje bleeding.",
            "effect": {"hits": 4, "dmg_pct_each": 0.40, "apply_bleed": True},
        },
        {
            "key": "shadow_step",
            "name": "Stínový Krok",
            "emoji": "👤",
            "level_req": 25,
            "desc": "Každé 4. kolo: garantovaný protiútok za 1.5× poškození + krvácení.",
            "effect": {"counter_dmg_mult": 1.5, "apply_bleed": True},
        },
        {
            "key": "mark_for_death",
            "name": "Označení Smrtí",
            "emoji": "🎯",
            "level_req": 25,
            "desc": "Každé 4. kolo: trvale snižuje DEF nepřítele o 25%.",
            "effect": {"def_reduction_pct": 0.25},
        },
    ],
}


def get_t2_options(cls: str) -> list[dict]:
    """Vrátí dostupné T2 talenty pro danou třídu."""
    return TALENT_T2_TREE.get(cls, [])
