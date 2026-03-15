"""
game/factions.py — Definice frakcí, renown tiery a balancovaný systém odměn
"""

# ── Frakce ─────────────────────────────────────────────────────────────────────
# Tři temné frakce — každá stejně silná, jen jinak zaměřená.
FACTIONS = {
    "rad_popele": {
        "id":          "rad_popele",
        "name":        "Řád Popele",
        "emblem":      "🔥",
        "color":       "#c0392b",
        "color_dim":   "rgba(192,57,43,0.15)",
        "tagline":     "Svět musí hořet, aby mohl být znovu zrozen.",
        "description": (
            "Fanatičtí válečníci přesvědčení, že spása přijde skrze totální destrukci. "
            "Sbírají sílu z ruin a zkázy. Jejich disciplína je nesmrtelná — jako oheň, "
            "který stráví vše, co mu stojí v cestě."
        ),
        "lore": "Základán legendárním generálem Kael'Vorem po pádu Prvního království.",
    },
    "pakt_stinu": {
        "id":          "pakt_stinu",
        "name":        "Pakt Stínu",
        "emblem":      "🌑",
        "color":       "#6c3483",
        "color_dim":   "rgba(108,52,131,0.15)",
        "tagline":     "Ve tmě nezanecháme stopy. Jsme stín — jsme všude.",
        "description": (
            "Tajná organizace lovců stínů a nekromantů. Sbírají moc z mrtvých a noci. "
            "Věří, že pravá svoboda leží v neviditelnosti — nikdo nemůže vládnout tomu, "
            "co nevidí."
        ),
        "lore": "Vznikl z trosek staré gildy vrahů po Druhé éře temnoty.",
    },
    "kongregace_prazdna": {
        "id":          "kongregace_prazdna",
        "name":        "Kongregace Prázdna",
        "emblem":      "🌀",
        "color":       "#1a6b8a",
        "color_dim":   "rgba(26,107,138,0.15)",
        "tagline":     "Za hranicí reality leží pravda. My jsme ji nalezli.",
        "description": (
            "Mystici a vědci zkoumající Prázdno — dimenzi za hranicí světa živých. "
            "Jejich magie přichází z chaosu a nicoty. Považují ostatní frakce za "
            "primitivy, kteří hledají moc na špatném místě."
        ),
        "lore": "Kongregace existuje od dob Starých Bohů — nebo tak tvrdí jejich záznamy.",
    },
}

# ── Renown tiery (stejná struktura pro všechny frakce) ─────────────────────────
# (tier_id, min_rep, name_cz)
RENOWN_TIERS = [
    (1,    0, "Neznámý"),
    (2,  100, "Poznaný"),
    (3,  300, "Důvěrník"),
    (4,  600, "Spojenec"),
    (5, 1000, "Šampión"),
    (6, 1500, "Legenda"),
]

# ── Odměny per frakce per tier ──────────────────────────────────────────────────
# BALANCE KLÍČ:
#   Tier 2 → 300g                    (všechny stejně)
#   Tier 3 → Kosmetický titul        (jiný, ale stejná hodnota)
#   Tier 4 → Elixír 3 dny           (různé staty, celkový součet +8 pro všechny)
#   Tier 5 → 1000g                   (všechny stejně)
#   Tier 6 → 2000g + Legendary titul (jiný, ale stejná hodnota)
# ─────────────────────────────────────────────────────────────────────────────
FACTION_REWARDS = {
    "rad_popele": {
        2: {
            "type": "gold", "amount": 300,
            "label": "300 Zlatých",
            "icon": "💰",
        },
        3: {
            "type": "title", "title": "Popelový Válečník",
            "label": "Titul: [Popelový Válečník]",
            "icon": "🏅",
        },
        4: {
            "type": "elixir", "name": "Elixír Zkázy",
            "bonuses": {"bonus_str": 5, "bonus_end": 3},
            "duration_days": 3,
            "label": "Elixír Zkázy (+5 Síla, +3 Výdrž, 3 dny)",
            "icon": "🧪",
        },
        5: {
            "type": "gold", "amount": 1000,
            "label": "1000 Zlatých",
            "icon": "💰",
        },
        6: {
            "type": "title_gold", "title": "Posel Zkázy", "bonus_gold": 2000,
            "label": "Titul: [Posel Zkázy] + 2000 Zlatých",
            "icon": "👑",
        },
    },
    "pakt_stinu": {
        2: {
            "type": "gold", "amount": 300,
            "label": "300 Zlatých",
            "icon": "💰",
        },
        3: {
            "type": "title", "title": "Stínový Lovec",
            "label": "Titul: [Stínový Lovec]",
            "icon": "🏅",
        },
        4: {
            "type": "elixir", "name": "Elixír Stínu",
            "bonuses": {"bonus_dex": 5, "bonus_luck": 3},
            "duration_days": 3,
            "label": "Elixír Stínu (+5 Obratnost, +3 Štěstí, 3 dny)",
            "icon": "🧪",
        },
        5: {
            "type": "gold", "amount": 1000,
            "label": "1000 Zlatých",
            "icon": "💰",
        },
        6: {
            "type": "title_gold", "title": "Pán Temnoty", "bonus_gold": 2000,
            "label": "Titul: [Pán Temnoty] + 2000 Zlatých",
            "icon": "👑",
        },
    },
    "kongregace_prazdna": {
        2: {
            "type": "gold", "amount": 300,
            "label": "300 Zlatých",
            "icon": "💰",
        },
        3: {
            "type": "title", "title": "Žák Prázdna",
            "label": "Titul: [Žák Prázdna]",
            "icon": "🏅",
        },
        4: {
            "type": "elixir", "name": "Elixír Prázdna",
            "bonuses": {"bonus_int": 5, "bonus_luck": 3},
            "duration_days": 3,
            "label": "Elixír Prázdna (+5 Inteligence, +3 Štěstí, 3 dny)",
            "icon": "🧪",
        },
        5: {
            "type": "gold", "amount": 1000,
            "label": "1000 Zlatých",
            "icon": "💰",
        },
        6: {
            "type": "title_gold", "title": "Hlas Prázdna", "bonus_gold": 2000,
            "label": "Titul: [Hlas Prázdna] + 2000 Zlatých",
            "icon": "👑",
        },
    },
}

# ── Reputace z aktivit ─────────────────────────────────────────────────────────
REP_FROM_QUEST = {
    "easy":      5,
    "normal":   10,
    "hard":     15,
    "elite":    20,
    "legendary":25,
    "boss":      8,  # boss questy dávají méně — jsou speciální
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_current_tier(reputation: int) -> dict:
    """Vrátí aktuální tier pro danou reputaci."""
    current = {"tier": RENOWN_TIERS[0][0], "min_rep": RENOWN_TIERS[0][1], "name": RENOWN_TIERS[0][2]}
    for tier_id, min_rep, name in RENOWN_TIERS:
        if reputation >= min_rep:
            current = {"tier": tier_id, "min_rep": min_rep, "name": name}
        else:
            break
    return current


def get_next_tier(reputation: int) -> dict | None:
    """Vrátí další tier nebo None pokud je hráč na maximu."""
    for tier_id, min_rep, name in RENOWN_TIERS:
        if reputation < min_rep:
            return {"tier": tier_id, "min_rep": min_rep, "name": name}
    return None
