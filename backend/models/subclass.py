"""
models/subclass.py — Definice specializací (subclassů) pro každou třídu.

Specializace se odemkne na level 10. Každá třída má 2 možnosti.
Volba je trvalá a nelze ji změnit.
"""

# ── Definice subclassů ────────────────────────────────────────────────────────
SUBCLASS_DEFINITIONS: dict[str, dict] = {

    # ── Warrior ─────────────────────────────────────────────────────────────
    "berserker": {
        "name":        "Berserkr",
        "cls":         "warrior",
        "emoji":       "🔴",
        "description": (
            "Obětuje obranu za drtivou útočnou sílu. Každý silný úder "
            "bolí oba — útočníka i bráněného."
        ),
        "flavor":      "Krev za krev. Vítěz bere vše.",
        # Stat multiplikátory (aplikují se v recalculate_stats)
        "stat_mults": {
            "dmg_mult":   1.10,   # +10 % DMG (bylo +20 %, sníženo pro balance)
            "armor_mult": 0.85,   # −15 % armor
        },
        "unlock_level": 10,
    },

    "guardian": {
        "name":        "Strážce",
        "cls":         "warrior",
        "emoji":       "🛡️",
        "description": (
            "Neprostupná zeď. Vydává se za cíl a absorbuje útoky štítem. "
            "Pomalejší ofenziva, ale takřka nezastavitelná obrana."
        ),
        "flavor":      "Nikdo neprojde, dokud dýchám.",
        "stat_mults": {
            "armor_mult": 1.20,   # +20 % armor (bylo +35 %)
            "hp_mult":    1.00,   # +0 % HP (bylo +20 %)
            "dmg_mult":   0.95,   # −5 % DMG
        },
        "unlock_level": 10,
    },

    # ── Mage ────────────────────────────────────────────────────────────────
    "elementalist": {
        "name":        "Elementalista",
        "cls":         "mage",
        "emoji":       "☄️",
        "description": (
            "Mistr arkanní magie. Každý druhý útok spouští Arkanní Přetížení — "
            "silný burst s ignorováním obrany. Konzistentní a předvídatelný výstup."
        ),
        "flavor":      "Magie není nástroj. Je to část mě.",
        "stat_mults": {
            "dmg_mult": 1.15,  # +15 % DMG (bylo +10 %, zvýšeno pro balance)
        },
        "unlock_level": 10,
    },

    "necromancer": {
        "name":        "Nekromancer",
        "cls":         "mage",
        "emoji":       "☠️",
        "description": (
            "Čerpá moc ze své vlastní smrtelnosti. Pod 30 % HP se transformuje — "
            "Dark Transformation přidá +40 % DMG permanentně. Life Drain na každém útoku."
        ),
        "flavor":      "Smrt není konec. Je to počátek.",
        "stat_mults": {
        },
        "unlock_level": 10,
    },

    # ── Ranger ──────────────────────────────────────────────────────────────
    "sharpshooter": {
        "name":        "Ostrostřelec",
        "cls":         "ranger",
        "emoji":       "💥",
        "description": (
            "Precizní střelec zaměřující se na smrtelná místa. "
            "Každý výstřel míří přesně — a kritické zásahy jsou devastující."
        ),
        "flavor":      "Jeden výstřel. Jeden cíl. Konec.",
        "stat_mults": {
            "dmg_mult":   1.10,  # +10 % DMG
            "luck_mult":  1.20,  # +20 % LUCK (combat only — v _FighterState)
            "armor_mult": 0.90,  # −10 % armor
        },
        "unlock_level": 10,
    },

    "shadowblade": {
        "name":        "Stínová Čepel",
        "cls":         "ranger",
        "emoji":       "🌑",
        "description": (
            "Rychlý jako stín. Teleportuje se za nepřítele a útočí "
            "dvěma rychlými ranami ze tmy. Zanechává krvácení. "
            "Zvýšený štěstí zajišťuje více kritických zásahů — každý z nich je devastující."
        ),
        "flavor":      "Nevidíš mě. Dokud není pozdě.",
        "stat_mults": {
            "armor_mult": 0.90,  # −10 % armor
            "dmg_mult":   1.12,  # +12 % DMG (bylo +5 %, zvýšeno pro balance)
            "luck_mult":  1.10,  # +10 % LUCK — synergy s bleed a crit
            "crit_mult":  1.20,  # +20 % crit damage (vizuální, dle enginu)
        },
        "unlock_level": 10,
    },
}

# Pomocný lookup: subclassy dostupné pro danou třídu
SUBCLASSES_BY_CLASS: dict[str, list[str]] = {}
for _key, _sdef in SUBCLASS_DEFINITIONS.items():
    _cls = _sdef["cls"]
    SUBCLASSES_BY_CLASS.setdefault(_cls, []).append(_key)
