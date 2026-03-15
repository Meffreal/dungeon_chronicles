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
            "atk_mult": 1.30,   # +30 % ATK
            "def_mult": 0.85,   # −15 % DEF
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
            "def_mult": 1.35,   # +35 % DEF
            "hp_mult":  1.20,   # +20 % HP
            "atk_mult": 0.90,   # −10 % ATK
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
            "atk_mult": 1.25,   # +25 % ATK
            "mp_mult":  1.15,   # +15 % MP
            "def_mult": 0.90,   # −10 % DEF
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
            "mp_mult":  1.30,   # +30 % MP
            "spd_mult": 1.10,   # +10 % SPD
            "atk_mult": 0.85,   # −15 % ATK
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
            "atk_mult":  1.20,  # +20 % ATK
            "luck_mult": 1.30,  # +30 % LUCK (combat only — v _FighterState)
            "def_mult":  0.90,  # −10 % DEF
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
            "spd_mult": 1.35,   # +35 % SPD
            "def_mult": 0.90,   # −10 % DEF
            "atk_mult": 0.95,   # −5 % ATK
        },
        "unlock_level": 10,
    },
}

# Pomocný lookup: subclassy dostupné pro danou třídu
SUBCLASSES_BY_CLASS: dict[str, list[str]] = {}
for _key, _sdef in SUBCLASS_DEFINITIONS.items():
    _cls = _sdef["cls"]
    SUBCLASSES_BY_CLASS.setdefault(_cls, []).append(_key)
