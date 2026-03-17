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
            "dmg_mult":   1.30,   # +30 % DMG
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
            "armor_mult": 1.35,   # +35 % armor
            "hp_mult":    1.20,   # +20 % HP
            "dmg_mult":   0.90,   # −10 % DMG
        },
        "unlock_level": 10,
    },

    # ── Mage ────────────────────────────────────────────────────────────────
    "elementalist": {
        "name":        "Elementalista",
        "cls":         "mage",
        "emoji":       "☄️",
        "description": (
            "Ovládá síly ohně, ledu a blesku. Kombinovaná kouzla jsou "
            "devastující — ale spotřebují mnoho many."
        ),
        "flavor":      "Příroda je zbraň. Já jsem spouštěč.",
        "stat_mults": {
            "dmg_mult":   1.25,   # +25 % DMG
            "armor_mult": 0.90,   # −10 % armor
        },
        "unlock_level": 10,
    },

    "necromancer": {
        "name":        "Nekromancer",
        "cls":         "mage",
        "emoji":       "☠️",
        "description": (
            "Čerpá moc z utrpení a death magic. Slabší přímý útok, "
            "ale kombinuje jed, krvácení a oslabení — nepřítel umírá pomalu."
        ),
        "flavor":      "Smrt není konec. Je to nástroj.",
        "stat_mults": {
            "dmg_mult": 0.85,   # −15 % DMG
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
            "dmg_mult":   1.20,  # +20 % DMG
            "luck_mult":  1.30,  # +30 % LUCK (combat only — v _FighterState)
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
            "dvěma rychlými ranami ze tmy. Zanechává krvácení."
        ),
        "flavor":      "Nevidíš mě. Dokud není pozdě.",
        "stat_mults": {
            "armor_mult": 0.90,  # −10 % armor
            "dmg_mult":   0.95,  # −5 % DMG
            "crit_mult":  1.35,  # +35 % crit damage
        },
        "unlock_level": 10,
    },
}

# Pomocný lookup: subclassy dostupné pro danou třídu
SUBCLASSES_BY_CLASS: dict[str, list[str]] = {}
for _key, _sdef in SUBCLASS_DEFINITIONS.items():
    _cls = _sdef["cls"]
    SUBCLASSES_BY_CLASS.setdefault(_cls, []).append(_key)
