"""
models/sets.py — Setové itemy (3pc/5pc bonusy)

Tři sety — jeden per povolání:
  Dračí Šupiny   (warrior): 3pc +15% HP, 5pc Regen každé kolo
  Bouřební Závoj (mage):    3pc +20% dmg schopností, 5pc Spell Echo 50%
  Přízračný Chodec (ranger): 3pc +12% LUCK, 5pc First Strike vždy
"""

SET_COLOR = "#00d4ff"  # Jednotná barva všech setových itemů (cyan — odlišná od všech rarit)

# Definice setů — každé povolání má svůj unikátní set
SET_DEFINITIONS = {
    1: {
        "id":     1,
        "name":   "Dračí Šupiny",
        "cls":    "warrior",
        "color":  SET_COLOR,
        "badge":  "🐉",
        "desc":   "Legendární šupiny draka ukuté do výzbroje. V kombinaci propůjčují nepřekonatelnou výdrž a přirozenou regeneraci.",
        "bonus_3pc":      {"hp_pct": 15},
        "bonus_5pc":      {"regen_every_round": True},
        "bonus_3pc_desc": "+15% max HP",
        "bonus_5pc_desc": "Regenerace každé kolo souboje (5% HP/kolo)",
        # Interní effect klíče pro combat engine a recalculate_with_gear
        "effect_3pc_hp_pct":   15,    # stat bonus: +15% HP (v recalculate_with_gear)
        "effect_5pc_regen":    True,  # combat: regenerace každé kolo (30 kol)
    },
    2: {
        "id":     2,
        "name":   "Bouřební Závoj",
        "cls":    "mage",
        "color":  SET_COLOR,
        "badge":  "⚡",
        "desc":   "Tkaný z čisté bouřkové magie. V kombinaci zesiluje ničivou moc kouzel a umožňuje jejich opakování.",
        "bonus_3pc":      {"ability_dmg_pct": 20},
        "bonus_5pc":      {"spell_echo_pct": 50},
        "bonus_3pc_desc": "+20% poškození schopností",
        "bonus_5pc_desc": "Spell Echo: 50% šance opakovat kouzlo",
        # Interní effect klíče
        "effect_3pc_ability_dmg_pct": 20,   # combat: bonus % dmg schopností
        "effect_5pc_spell_echo_pct":  50,   # combat: Spell Echo šance v %
    },
    3: {
        "id":     3,
        "name":   "Přízračný Chodec",
        "cls":    "ranger",
        "color":  SET_COLOR,
        "badge":  "👁",
        "desc":   "Výzbroj tichého lovce z temnoty. V kombinaci zostřuje smysly a zaručuje první úder v každém souboji.",
        "bonus_3pc":      {"luck_pct": 12},
        "bonus_5pc":      {"first_strike": True},
        "bonus_3pc_desc": "+12% Štěstí",
        "bonus_5pc_desc": "Vždy útočíš jako první v souboji",
        # Interní effect klíče
        "effect_3pc_luck_pct":      12,    # stat bonus: +12% LUCK (v recalculate_with_gear)
        "effect_5pc_first_strike":  True,  # combat: zaručený první útok
    },
}

# Rychlý lookup: class → set_id
CLS_TO_SET_ID: dict[str, int] = {sdef["cls"]: sid for sid, sdef in SET_DEFINITIONS.items()}


def get_active_set_bonuses(equipped_items: list, char_cls: str) -> dict:
    """
    Spočítá aktivní set bonusy pro danou postavu.
    equipped_items: list of Item ORM objektů (může obsahovat None).

    Vrátí dict:
      "active"          — {set_id: info_dict} s aktivními sety a efekty
      "hp_multiplier"   — multiplikátor pro HP stat (z 3pc Dračích Šupin)
      "luck_multiplier" — multiplikátor pro LUCK stat (z 3pc Přízračného Chodce)
      "total_atk_multiplier" — zachováno pro zpětnou compat (vždy 1.0)
    """
    from collections import Counter
    set_counts: Counter = Counter()

    for item in equipped_items:
        if item and getattr(item, "set_id", None):
            sdef = SET_DEFINITIONS.get(item.set_id)
            if sdef and sdef["cls"] == char_cls:
                set_counts[item.set_id] += 1

    active: dict = {}
    hp_multiplier   = 1.0
    luck_multiplier = 1.0

    for set_id, count in set_counts.items():
        sdef = SET_DEFINITIONS[set_id]
        info: dict = {
            "set_id":           set_id,
            "set_name":         sdef["name"],
            "cls":              sdef["cls"],
            "color":            sdef["color"],
            "badge":            sdef["badge"],
            "pieces_equipped":  count,
            "bonus_3pc_active": count >= 3,
            "bonus_5pc_active": count >= 5,
            "bonus_3pc_desc":   sdef["bonus_3pc_desc"],
            "bonus_5pc_desc":   sdef["bonus_5pc_desc"],
            # Combat effects — výchozí hodnoty (přepsány níže dle aktivních bonusů)
            "hp_pct":            0,
            "luck_pct":          0,
            "ability_dmg_pct":   0,
            "regen_every_round": False,
            "spell_echo_pct":    0,
            "first_strike":      False,
        }

        if count >= 3:
            info["hp_pct"]          = sdef.get("effect_3pc_hp_pct", 0)
            info["luck_pct"]        = sdef.get("effect_3pc_luck_pct", 0)
            info["ability_dmg_pct"] = sdef.get("effect_3pc_ability_dmg_pct", 0)
            if info["hp_pct"]:
                hp_multiplier   *= 1.0 + info["hp_pct"] / 100.0
            if info["luck_pct"]:
                luck_multiplier *= 1.0 + info["luck_pct"] / 100.0

        if count >= 5:
            info["regen_every_round"] = bool(sdef.get("effect_5pc_regen",         False))
            info["spell_echo_pct"]    = int( sdef.get("effect_5pc_spell_echo_pct", 0))
            info["first_strike"]      = bool(sdef.get("effect_5pc_first_strike",   False))

        active[set_id] = info

    return {
        "active":               active,
        "hp_multiplier":        round(hp_multiplier,   4),
        "luck_multiplier":      round(luck_multiplier, 4),
        "total_atk_multiplier": 1.0,   # zachováno pro zpětnou compat
    }
