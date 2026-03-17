"""
models/runosmith.py — Runovník: definice run a jejich inscripce na inventářní předměty
"""
import json
from datetime import datetime, timedelta
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Seed data: definice run ───────────────────────────────────────────────────
# effect_json klíče odpovídají bonus_* sloupcům v Item modelu + "bonus_quest_success_pct"

RUNE_DEFINITIONS = [
    # ── Tier 1 (Rank Runovníka: 1) ──────────────────────────────────────────
    {"key": "rune_fire_1",    "name": "Ohnivá runa I",     "tier": 1, "rank_required": 1, "icon": "🔥",
     "effect": {"bonus_atk": 3},
     "resonance_to_evolve": 50,  "evolves_to": "rune_fire_2"},

    {"key": "rune_shadow_1",  "name": "Stínová runa I",    "tier": 1, "rank_required": 1, "icon": "🌑",
     "effect": {"bonus_dex": 3},
     "resonance_to_evolve": 50,  "evolves_to": "rune_shadow_2"},

    {"key": "rune_void_1",    "name": "Runa Prázdna I",    "tier": 1, "rank_required": 1, "icon": "💜",
     "effect": {"bonus_def": 3},
     "resonance_to_evolve": 50,  "evolves_to": "rune_void_2"},

    {"key": "rune_life_1",    "name": "Runa Života I",     "tier": 1, "rank_required": 1, "icon": "💚",
     "effect": {"bonus_hp": 20},
     "resonance_to_evolve": 50,  "evolves_to": "rune_life_2"},

    # ── Tier 2 (Rank: 2) ────────────────────────────────────────────────────
    {"key": "rune_fire_2",    "name": "Ohnivá runa II",    "tier": 2, "rank_required": 2, "icon": "🔥",
     "effect": {"bonus_atk": 8, "bonus_str": 2},
     "resonance_to_evolve": 150, "evolves_to": "rune_fire_3"},

    {"key": "rune_shadow_2",  "name": "Stínová runa II",   "tier": 2, "rank_required": 2, "icon": "🌑",
     "effect": {"bonus_dex": 10},
     "resonance_to_evolve": 150, "evolves_to": "rune_shadow_3"},

    {"key": "rune_void_2",    "name": "Runa Prázdna II",   "tier": 2, "rank_required": 2, "icon": "💜",
     "effect": {"bonus_def": 8, "bonus_end": 2},
     "resonance_to_evolve": 150, "evolves_to": "rune_void_3"},

    {"key": "rune_life_2",    "name": "Runa Života II",    "tier": 2, "rank_required": 2, "icon": "💚",
     "effect": {"bonus_hp": 50, "bonus_end": 3},
     "resonance_to_evolve": 150, "evolves_to": "rune_life_3"},

    # ── Tier 3 (Rank: 3) ────────────────────────────────────────────────────
    {"key": "rune_fire_3",    "name": "Ohnivá runa III",   "tier": 3, "rank_required": 3, "icon": "🔥",
     "effect": {"bonus_atk": 16, "bonus_str": 5, "bonus_luck": 2},
     "resonance_to_evolve": 350, "evolves_to": "rune_fire_4"},

    {"key": "rune_shadow_3",  "name": "Stínová runa III",  "tier": 3, "rank_required": 3, "icon": "🌑",
     "effect": {"bonus_dex": 21, "bonus_luck": 2},
     "resonance_to_evolve": 350, "evolves_to": "rune_shadow_4"},

    {"key": "rune_void_3",    "name": "Runa Prázdna III",  "tier": 3, "rank_required": 3, "icon": "💜",
     "effect": {"bonus_def": 16, "bonus_end": 5, "bonus_hp": 30},
     "resonance_to_evolve": 350, "evolves_to": "rune_void_4"},

    {"key": "rune_arcane_3",  "name": "Arkánní runa III",  "tier": 3, "rank_required": 3, "icon": "⚡",
     "effect": {"bonus_luck": 60, "bonus_int": 5},
     "resonance_to_evolve": 350, "evolves_to": "rune_arcane_4"},

    # ── Tier 4 (Rank: 4) ────────────────────────────────────────────────────
    {"key": "rune_fire_4",    "name": "Ohnivá runa IV",    "tier": 4, "rank_required": 4, "icon": "🔥",
     "effect": {"bonus_atk": 28, "bonus_str": 9, "bonus_luck": 4},
     "resonance_to_evolve": 700, "evolves_to": "rune_fire_5"},

    {"key": "rune_shadow_4",  "name": "Stínová runa IV",   "tier": 4, "rank_required": 4, "icon": "🌑",
     "effect": {"bonus_dex": 37, "bonus_luck": 4},
     "resonance_to_evolve": 700, "evolves_to": "rune_shadow_5"},

    {"key": "rune_void_4",    "name": "Runa Prázdna IV",   "tier": 4, "rank_required": 4, "icon": "💜",
     "effect": {"bonus_def": 28, "bonus_end": 9, "bonus_hp": 80},
     "resonance_to_evolve": 700, "evolves_to": "rune_void_5"},

    {"key": "rune_arcane_4",  "name": "Arkánní runa IV",   "tier": 4, "rank_required": 4, "icon": "⚡",
     "effect": {"bonus_luck": 123, "bonus_int": 9},
     "resonance_to_evolve": 700, "evolves_to": "rune_arcane_5"},

    # ── Tier 5 – Legendární (Rank: 5) ────────────────────────────────────────
    {"key": "rune_fire_5",    "name": "Věčný Plamen",      "tier": 5, "rank_required": 5, "icon": "🔥",
     "effect": {"bonus_atk": 45, "bonus_str": 14, "bonus_luck": 7},
     "resonance_to_evolve": None, "evolves_to": None},

    {"key": "rune_shadow_5",  "name": "Stín Věčnosti",     "tier": 5, "rank_required": 5, "icon": "🌑",
     "effect": {"bonus_dex": 59, "bonus_luck": 7},
     "resonance_to_evolve": None, "evolves_to": None},

    {"key": "rune_void_5",    "name": "Prázdnota",         "tier": 5, "rank_required": 5, "icon": "💜",
     "effect": {"bonus_def": 40, "bonus_end": 14, "bonus_hp": 150},
     "resonance_to_evolve": None, "evolves_to": None},

    {"key": "rune_arcane_5",  "name": "Arkánní Singularita","tier": 5, "rank_required": 5, "icon": "⚡",
     "effect": {"bonus_luck": 200, "bonus_int": 14, "bonus_atk": 15},
     "resonance_to_evolve": None, "evolves_to": None},

    {"key": "rune_soul",      "name": "Runa Duše",          "tier": 5, "rank_required": 5, "icon": "⭐",
     "effect": {"bonus_atk": 20, "bonus_def": 20, "bonus_dex": 20, "bonus_luck": 10},
     "resonance_to_evolve": None, "evolves_to": None},
]

# ── Kombinace run (synergy / conflict) ────────────────────────────────────────
# Zkontrolováno při inscripci druhé runy na předmět (rank 3+ Runovníka).

RUNE_COMBINATIONS = [
    # Konflikty
    {"rune_a": "rune_fire_2",   "rune_b": "rune_void_2",   "type": "conflict",
     "description": "Oheň a Prázdno se vzájemně potlačují. Oba efekty −50%."},
    {"rune_a": "rune_fire_3",   "rune_b": "rune_void_3",   "type": "conflict",
     "description": "Oheň a Prázdno se vzájemně potlačují. Oba efekty −50%."},

    # Synergy
    {"rune_a": "rune_fire_2",   "rune_b": "rune_life_2",   "type": "synergy",
     "bonus": {"bonus_atk": 5, "bonus_hp": 20},
     "description": "Životní plamen: +5 ATK a +20 HP navíc."},

    {"rune_a": "rune_void_2",   "rune_b": "rune_shadow_2", "type": "synergy",
     "bonus": {"bonus_dex": 6, "bonus_def": 4},
     "description": "Prázdnota stínů: +6 DEX a +4 DEF navíc."},

    {"rune_a": "rune_arcane_3", "rune_b": "rune_life_3",   "type": "synergy",
     "bonus": {"bonus_luck": 40, "bonus_hp": 40},
     "description": "Arkánní vitalita: +40 LUCK a +40 HP navíc."},

    {"rune_a": "rune_fire_4",   "rune_b": "rune_shadow_4", "type": "synergy",
     "bonus": {"bonus_atk": 15, "bonus_dex": 10, "bonus_luck": 5},
     "description": "Hořící stín: +15 ATK, +10 DEX, +5 LUCK navíc."},
]

RUNE_COMBINATION_LOOKUP: dict[tuple[str, str], dict] = {}
for _combo in RUNE_COMBINATIONS:
    _a, _b = _combo["rune_a"], _combo["rune_b"]
    RUNE_COMBINATION_LOOKUP[(_a, _b)] = _combo
    RUNE_COMBINATION_LOOKUP[(_b, _a)] = _combo   # symetrické

# Max run na jeden předmět (odemkne se na Rank 3)
MAX_RUNES_PER_ITEM = 2

# Cooldown: stejná kombinace runa+předmět nesmí generovat XP dvakrát za 24h
RUNE_XP_COOLDOWN_HOURS = 24


# ── DB modely ─────────────────────────────────────────────────────────────────

class Rune(Base):
    """Definice runy (seed data). Nepřiřazena konkrétnímu hráči."""
    __tablename__ = "runes"

    id:                  Mapped[int]       = mapped_column(primary_key=True)
    key:                 Mapped[str]       = mapped_column(String(64), unique=True, index=True)
    name:                Mapped[str]       = mapped_column(String(64))
    tier:                Mapped[int]       = mapped_column(Integer)           # 1–5
    rank_required:       Mapped[int]       = mapped_column(Integer)           # min rank Runovníka
    icon:                Mapped[str]       = mapped_column(String(8), default="✦")
    effect_json:         Mapped[str]       = mapped_column(Text)              # {"bonus_atk": 5, ...}
    resonance_to_evolve: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evolves_to:          Mapped[str | None] = mapped_column(String(64), nullable=True)  # key cílové runy

    def to_dict(self) -> dict:
        return {
            "id":                  self.id,
            "key":                 self.key,
            "name":                self.name,
            "tier":                self.tier,
            "icon":                self.icon,
            "rank_required":       self.rank_required,
            "effect":              json.loads(self.effect_json) if self.effect_json else {},
            "resonance_to_evolve": self.resonance_to_evolve,
            "evolves_to":          self.evolves_to,
        }


class ItemRune(Base):
    """
    Runa inscribovaná na konkrétní InventoryItem (instanci předmětu).
    Na jednom předmětu mohou být max 2 runy (slot 1 a slot 2).
    Runovník Rank 3+ může inscribovat druhou runu – systém pak vyhodnotí kombinaci.
    """
    __tablename__ = "item_runes"
    __table_args__ = (UniqueConstraint("inventory_item_id", "slot"),)

    id:                   Mapped[int]       = mapped_column(primary_key=True)
    inventory_item_id:    Mapped[int]       = mapped_column(Integer, ForeignKey("inventory.id"))
    rune_id:              Mapped[int]       = mapped_column(Integer, ForeignKey("runes.id"))
    slot:                 Mapped[int]       = mapped_column(Integer, default=1)   # 1 nebo 2
    resonance:            Mapped[int]       = mapped_column(Integer, default=0)   # absorbovaná rezonance z boje
    inscribed_by_char_id: Mapped[int]       = mapped_column(Integer, ForeignKey("characters.id"))
    inscribed_at:         Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_xp_awarded_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # cooldown tracker

    # Výsledek kombinace (vyplní se při inscripci druhé runy)
    combination_type:     Mapped[str | None] = mapped_column(String(16), nullable=True)  # synergy | conflict | None

    inventory_item = relationship("InventoryItem")
    rune           = relationship("Rune")
    inscribed_by   = relationship("Character", foreign_keys=[inscribed_by_char_id])

    def add_resonance(self, amount: int) -> bool:
        """
        Přidá rezonanci. Vrátí True pokud runa dosáhla prahu pro evolve
        (logika evolve řeší router/service vrstva).
        """
        self.resonance += amount
        if self.rune and self.rune.resonance_to_evolve:
            return self.resonance >= self.rune.resonance_to_evolve
        return False

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "rune":             self.rune.to_dict() if self.rune else None,
            "slot":             self.slot,
            "resonance":        self.resonance,
            "resonance_needed": self.rune.resonance_to_evolve if self.rune else None,
            "inscribed_at":     self.inscribed_at.isoformat(),
            "combination_type": self.combination_type,
        }
