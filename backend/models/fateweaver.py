"""
models/fateweaver.py — Tkadlec Osudu: pouta mezi hráči a duchy, karma systém
"""
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────

BOND_DURATION_HOURS         = 72     # standardní pouto vydrží 3 dny
SPIRIT_BOND_DURATION_HOURS  = 72     # duchové také 3 dny
BOSS_SPIRIT_DURATION_HOURS  = 24     # duch guild boss monstera vydrží jen 24h

BOND_TARGET_COOLDOWN_HOURS  = 48    # cooldown: nové pouto se stejným cílem

# Karma limity (importovatelné i z profession.py, ale definujeme kanonicky zde)
KARMA_SOFT_CAP = 5    # karma >= 5: -5 % quest success rate (sdíleno s profession.py)
KARMA_HARD_CAP = 10   # karma >= 10: nemůže vytvářet nová pouta

KARMA_PER_CURSE   = 1   # každé prokletí přidá 1 karma bod
KARMA_PER_BLESS   = -1  # každé požehnání odebere 1 karma bod (min 0)

# Max aktivních pout (hráčských + duchových dohromady)
MAX_PLAYER_BONDS  = 3
MAX_SPIRIT_BONDS  = 2

# XP tabulka
FATEWEAVER_XP = {
    "bond_created_player": 50,
    "bond_created_spirit": 30,
    "bond_fired":          40,    # pouto se aktivovalo (oba uspěli)
    "bond_survived_7d":   150,
    "bond_survived_30d":  400,
    "curse_delivered":     80,
    "curse_blocked":        0,    # cíl měl ochranu
    "bond_dissolved":      20,    # na žádost klienta
}

# Typy pout
BOND_TYPES = [
    "cooperation",   # hráč↔hráč – sdílené XP bonusy ze questů
    "war_pact",      # hráč↔hráč – sdílené ATK bonusy v aréně
    "curse",         # hráč→hráč – snižuje quest success chance cíle (generuje karmu)
    "ancestral",     # hráč↔duch – NPC pouto s duchem padlého bojovníka
    "guild_bond",    # Rank 4+: propojí 3 hráče najednou (trojpouto)
]

# Duchové – archotypy pro NPC pouta
SPIRIT_TYPES = {
    "warrior": {
        "name":   "Duch Válečníka",
        "icon":   "⚔️",
        "effect": {"bonus_def_pct": 8, "bonus_hp_flat": 30},
        "description": "Starodávný bojovník chrání tvé tělo v questu.",
    },
    "mage": {
        "name":   "Duch Mága",
        "icon":   "🔮",
        "effect": {"bonus_mp_flat": 40, "bonus_spell_pct": 10},
        "description": "Archaická inteligence zesiluje tvá kouzla v aréně.",
    },
    "ranger": {
        "name":   "Duch Rangera",
        "icon":   "🏹",
        "effect": {"bonus_quest_speed_pct": 12, "bonus_drop_luck": 5},
        "description": "Lovec zrychluje tvůj postup a svými smysly cítí skryté poklady.",
    },
}


# ── Modely ────────────────────────────────────────────────────────────────────

class FateBond(Base):
    """
    Jedno pouto vytvořené Tkadlecem. Může být:
    - hráč↔hráč (target_a_char_id a target_b_char_id vyplněny)
    - hráč↔duch (spirit_type vyplněn, target_a = hráč, target_b = None)
    - guild_bond (Rank 4+): target_a, target_b i třetí člen (uložen v effect_json)

    Každé pouto má effect_json s konkrétními bonusy aplikovanými na hráče.
    fire_count sleduje, kolikrát se pouto "aktivovalo" (XP zdroj).
    """
    __tablename__ = "fate_bonds"

    id:                Mapped[int] = mapped_column(primary_key=True)
    weaver_char_id:    Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))

    # Cíle pouta
    target_a_char_id:  Mapped[int | None] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)
    target_b_char_id:  Mapped[int | None] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)
    spirit_type:       Mapped[str | None] = mapped_column(String(16), nullable=True)   # warrior | mage | ranger
    is_boss_spirit:    Mapped[bool]       = mapped_column(Boolean, default=False)       # Rank 4+: guild boss duch

    bond_type:         Mapped[str]  = mapped_column(String(32))    # viz BOND_TYPES
    effect_json:       Mapped[str]  = mapped_column(Text)
    # Příklad: {"bonus_xp_pct": 10, "bonus_atk_pct": 8, "quest_success_penalty": -5}

    # Karma zaplacená při tvorbě tohoto pouta (záporné = požehnání ubralo karmu)
    karma_delta:       Mapped[int]  = mapped_column(Integer, default=0)

    created_at:        Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:        Mapped[datetime]      = mapped_column(DateTime)
    is_active:         Mapped[bool]          = mapped_column(Boolean, default=True)
    dissolved_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fire_count:        Mapped[int]            = mapped_column(Integer, default=0)
    xp_last_fire_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Milníkové XP (aby se nedávaly opakovaně)
    xp_7d_awarded:     Mapped[bool] = mapped_column(Boolean, default=False)
    xp_30d_awarded:    Mapped[bool] = mapped_column(Boolean, default=False)

    weaver   = relationship("Character", foreign_keys=[weaver_char_id])
    target_a = relationship("Character", foreign_keys=[target_a_char_id])
    target_b = relationship("Character", foreign_keys=[target_b_char_id])

    # ── Factory helpers ───────────────────────────────────────────────────────

    @classmethod
    def create_player_bond(cls, weaver_id: int, target_a_id: int, target_b_id: int,
                           bond_type: str, effect: dict, karma_delta: int) -> "FateBond":
        return cls(
            weaver_char_id=weaver_id,
            target_a_char_id=target_a_id,
            target_b_char_id=target_b_id,
            bond_type=bond_type,
            effect_json=json.dumps(effect),
            karma_delta=karma_delta,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=BOND_DURATION_HOURS),
        )

    @classmethod
    def create_spirit_bond(cls, weaver_id: int, target_char_id: int,
                           spirit_type: str, is_boss: bool = False) -> "FateBond":
        spirit = SPIRIT_TYPES.get(spirit_type, {})
        effect = spirit.get("effect", {})
        hours  = BOSS_SPIRIT_DURATION_HOURS if is_boss else SPIRIT_BOND_DURATION_HOURS
        return cls(
            weaver_char_id=weaver_id,
            target_a_char_id=target_char_id,
            spirit_type=spirit_type,
            is_boss_spirit=is_boss,
            bond_type="ancestral",
            effect_json=json.dumps(effect),
            karma_delta=0,
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=hours),
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc).replace(tzinfo=None) > self.expires_at.replace(tzinfo=None)

    @property
    def is_currently_active(self) -> bool:
        return self.is_active and not self.is_expired and self.dissolved_at is None

    @property
    def days_active(self) -> int:
        end = self.dissolved_at or datetime.now(timezone.utc).replace(tzinfo=None)
        return (end.replace(tzinfo=None) - self.created_at.replace(tzinfo=None)).days

    def get_effect(self) -> dict:
        try:
            return json.loads(self.effect_json)
        except Exception:
            return {}

    def dissolve(self) -> None:
        self.is_active = False
        self.dissolved_at = datetime.now(timezone.utc).replace(tzinfo=None)

    def register_fire(self) -> None:
        """Zaregistruje aktivaci pouta (XP spravuje service vrstva)."""
        self.fire_count += 1
        self.xp_last_fire_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "bond_type":    self.bond_type,
            "spirit_type":  self.spirit_type,
            "is_boss_spirit": self.is_boss_spirit,
            "target_a_name": self.target_a.name if self.target_a else None,
            "target_b_name": self.target_b.name if self.target_b else None,
            "effect":       self.get_effect(),
            "created_at":   self.created_at.isoformat(),
            "expires_at":   self.expires_at.isoformat(),
            "is_active":    self.is_currently_active,
            "days_active":  self.days_active,
            "fire_count":   self.fire_count,
        }
