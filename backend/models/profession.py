"""
models/profession.py — Profesní systém: core tracking (naučené profese, rank, XP, sloty)
"""
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────

PROFESSION_KEYS = ["runist", "oracle", "broker"]

# Mapování starých klíčů na nové (pro migraci a backward compat)
PROFESSION_MIGRATION_MAP: dict[str, str] = {
    "runosmith":  "runist",
    "soulforger": "runist",
    "diviner":    "oracle",
    "fateweaver": "oracle",
    "gambler":    "broker",
    "agent":      "broker",
}

PROFESSION_META = {
    "runist": {
        "name":        "Runist",
        "icon":        "✦",
        "description": (
            "Mistr run a kování duší. Dvě aktivní schopnosti: "
            "✦ Inscripce run — vyrývá magické runy do vybavení, které časem sílí v boji. "
            "⚒ Soul Forge — taví existující předměty a z jejich esence kuje nové. "
            "Pasivní: Rezonance — vybavené runy automaticky absorbují bojovou energii."
        ),
    },
    "oracle": {
        "name":        "Věštec",
        "icon":        "🔮",
        "description": (
            "Čtenář nití osudu a tkadlec pout. Dvě aktivní schopnosti: "
            "📜 Proroctví — vytváří a prodává věštecké svitky, odměňován za přesnost. "
            "🌀 Pouta osudu — tká magická pouta mezi hráči i duchy na 72 hodin. "
            "Pasivní: Prozření — +2 % XP z questů za každý rank (max +10 % na rank 5)."
        ),
    },
    "broker": {
        "name":        "Makléř",
        "icon":        "🎲",
        "description": (
            "Mistr rizika a stínových operací. Dvě aktivní schopnosti: "
            "🎲 Sázky — uzavírá sázky na výsledky questů a arény, pořádá loterie. "
            "🕵 Operace — provádí tajné průzkumy, infiltrace a sabotáže. "
            "Pasivní: Riziková prémie — +5 % zlata z questů za každý rank (max +25 % na rank 5)."
        ),
    },
}

# Cena za naučení N-té profese (index = pořadí, 0-based; 1. a 2. jsou zdarma)
PROFESSION_LEARN_COSTS = [0, 0, 1500]

# XP potřeba pro přechod z ranku N na N+1 (index = aktuální rank)
RANK_XP_THRESHOLDS = [100, 400, 1000, 2500, 5000]

RANK_NAMES = ["Novic", "Učedník", "Tovaryš", "Expert", "Mistr", "Velmistr"]

MAX_RANK           = 5
ACTIVE_SLOTS       = 2          # hráč má vždy právě 2 aktivní profese
SLOT_COOLDOWN_HOURS = 48        # cooldown slotu po přepnutí profese

# Karma limity pro Tkadlece (globálně dostupné)
KARMA_SOFT_CAP = 5    # při karma >= 5: -5% quest success rate
KARMA_HARD_CAP = 10   # při karma >= 10: nemůže vytvářet nová pouta


# ── Model ─────────────────────────────────────────────────────────────────────

class CharacterProfession(Base):
    """Jeden záznam pro každou kombinaci (postava × profese). Max 6 záznamů na postavu."""
    __tablename__ = "character_professions"
    __table_args__ = (UniqueConstraint("character_id", "profession_key"),)

    id:             Mapped[int]  = mapped_column(primary_key=True)
    character_id:   Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"))
    profession_key: Mapped[str]  = mapped_column(String(32))   # jeden z PROFESSION_KEYS

    rank:           Mapped[int]  = mapped_column(Integer, default=0)   # 0–5
    xp:             Mapped[int]  = mapped_column(Integer, default=0)   # XP směrem k dalšímu ranku

    is_active:      Mapped[bool]          = mapped_column(Boolean, default=False)
    slot:           Mapped[int | None]    = mapped_column(Integer, nullable=True)   # 1 nebo 2; None = dormant

    learned_at:     Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # kdy byl vložen do aktivního slotu

    # Tkadlec: karma body za seslání prokletí (globálně sdílené přes tento sloupec)
    karma_points:   Mapped[int]  = mapped_column(Integer, default=0, server_default="0")

    character = relationship("Character", back_populates="professions")

    # ── Slot cooldown ────────────────────────────────────────────────────────

    @property
    def slot_locked_until(self) -> datetime | None:
        """Profese nesmí být deaktivována (vyňata ze slotu) dřív než 48h po aktivaci."""
        if self.activated_at is None:
            return None
        return self.activated_at + timedelta(hours=SLOT_COOLDOWN_HOURS)

    @property
    def can_deactivate(self) -> bool:
        until = self.slot_locked_until
        if until is None:
            return True
        return datetime.now(timezone.utc).replace(tzinfo=None) >= until

    # ── XP a rank ────────────────────────────────────────────────────────────

    @property
    def xp_to_next_rank(self) -> int | None:
        """XP potřeba pro přechod na následující rank. None pokud jsme na MAX_RANK."""
        if self.rank >= MAX_RANK:
            return None
        return RANK_XP_THRESHOLDS[self.rank]

    @property
    def rank_name(self) -> str:
        return RANK_NAMES[min(self.rank, len(RANK_NAMES) - 1)]

    def add_xp(self, amount: int) -> bool:
        """
        Přidá XP a zpracuje případný rank-up (může proběhnout i vícenásobný).
        Vrátí True pokud došlo k alespoň jednomu rank-up.
        """
        if self.rank >= MAX_RANK or amount <= 0:
            return False
        self.xp += amount
        ranked_up = False
        while self.rank < MAX_RANK and self.xp >= RANK_XP_THRESHOLDS[self.rank]:
            self.xp -= RANK_XP_THRESHOLDS[self.rank]
            self.rank += 1
            ranked_up = True
        return ranked_up

    # ── Karma (Tkadlec) ───────────────────────────────────────────────────────

    def add_karma(self, amount: int) -> None:
        self.karma_points = max(0, self.karma_points + amount)

    @property
    def karma_penalty_active(self) -> bool:
        return self.karma_points >= KARMA_SOFT_CAP

    @property
    def karma_blocked(self) -> bool:
        """Tkadlec nemůže vytvářet nová pouta."""
        return self.karma_points >= KARMA_HARD_CAP

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        meta = PROFESSION_META.get(self.profession_key, {})
        return {
            "profession_key":    self.profession_key,
            "name":              meta.get("name", self.profession_key),
            "icon":              meta.get("icon", "?"),
            "description":       meta.get("description", ""),
            "rank":              self.rank,
            "rank_name":         self.rank_name,
            "xp":                self.xp,
            "xp_to_next":        self.xp_to_next_rank,
            "is_active":         self.is_active,
            "slot":              self.slot,
            "can_deactivate":    self.can_deactivate,
            "slot_locked_until": self.slot_locked_until.isoformat() if self.slot_locked_until else None,
            "learned_at":        self.learned_at.isoformat(),
            "karma_points":      self.karma_points,
        }
