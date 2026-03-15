"""
models/gambler.py — Šarlatán: sázky (Bet), loterie (Lottery + LotteryEntry)
"""
from datetime import datetime, timedelta
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────

BET_MAX_OPEN        = 5      # max otevřených sázek najednou
BET_MIN_STAKE       = 100    # minimální sázka v zlatě
LOTTERY_MIN_PLAYERS = 3      # min účastníků aby mohla loterie proběhnout

# Shadow House edge (NPC bookmaker) – odds jsou vždy o tento % horší než férové
SHADOW_HOUSE_EDGE = 0.15

# Suspicion: po kolika výhrách v řadě se Shadow House zbystří
SHADOW_HOUSE_SUSPICION_THRESHOLD = 5
SHADOW_HOUSE_SUSPICION_ODDS_PENALTY = 0.10   # další -10 % na odds

# XP tabulka
GAMBLER_XP = {
    "bet_placed":          15,   # za uzavření sázky (jakýkoli výsledek)
    "bet_won_vs_player":   80,
    "bet_won_vs_npc":      48,   # 60 % sazby
    "bet_lost":             5,
    "market_transaction":  30,   # za každou black market transakci
    "lottery_organized":  200,   # flat, bez ohledu na výsledek
    "bet_won_underdog":    40,   # bonus za výhru vs silnějšímu (ELO+)
}

# Typy sázek
BET_TYPES = [
    "quest_success",       # hráč uspěje / selže v questu
    "quest_drop_rarity",   # rarity dropu z questu
    "arena_outcome",       # výsledek arénového útoku
    "shadow_house",        # speciální NPC sázka
]


# ── Modely ────────────────────────────────────────────────────────────────────

class Bet(Base):
    """
    Jedna sázka. Může být:
    - hráč vs. hráč (target_char_id vyplněno, is_vs_npc = False)
    - hráč vs. Shadow House (target_char_id = None, is_vs_npc = True)

    subject_id + subject_type určují, na co se sází (quest ID, arena match ID).
    Po dokončení questu/arény systém automaticky resolvuje sázky.
    """
    __tablename__ = "bets"

    id:                 Mapped[int] = mapped_column(primary_key=True)
    bettor_char_id:     Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    target_char_id:     Mapped[int | None] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)

    bet_type:           Mapped[str]        = mapped_column(String(32))    # viz BET_TYPES
    subject_id:         Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject_type:       Mapped[str | None] = mapped_column(String(32), nullable=True)  # "quest" | "arena"

    bettor_prediction:  Mapped[str] = mapped_column(String(64))   # "success" | "fail" | "epic" | ...
    bettor_stake:       Mapped[int] = mapped_column(Integer)       # zlato které Šarlatán vsadil
    # U hráč vs. hráč: target_stake = co vsadí protistrana
    # U Shadow House: target_stake = potenciální výhra (po odečtení edge)
    target_stake:       Mapped[int] = mapped_column(Integer)

    is_vs_npc:          Mapped[bool]  = mapped_column(Boolean, default=False)
    # Nakumulovaný suspicion penalty pro Shadow House sázky (0.0–1.0)
    npc_odds_penalty:   Mapped[float] = mapped_column(Float, default=0.0)

    status:             Mapped[str]          = mapped_column(String(16), default="open")
    # open | accepted | resolved | cancelled
    result:             Mapped[str | None]   = mapped_column(String(16), nullable=True)   # win | loss

    created_at:         Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at:        Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at:        Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    xp_awarded:         Mapped[bool] = mapped_column(Boolean, default=False)

    bettor = relationship("Character", foreign_keys=[bettor_char_id])
    target = relationship("Character", foreign_keys=[target_char_id])

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def opponent_label(self) -> str:
        if self.is_vs_npc:
            return "Shadow House"
        return self.target.name if self.target else "?"

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "bet_type":          self.bet_type,
            "subject_type":      self.subject_type,
            "subject_id":        self.subject_id,
            "bettor_prediction": self.bettor_prediction,
            "bettor_stake":      self.bettor_stake,
            "bettor_char_id":    self.bettor_char_id,
            "potential_win":     self.target_stake,
            "vs":                self.opponent_label,
            "is_vs_npc":         self.is_vs_npc,
            "status":            self.status,
            "result":            self.result,
            "created_at":        self.created_at.isoformat(),
            "resolved_at":       self.resolved_at.isoformat() if self.resolved_at else None,
        }


class Lottery(Base):
    """
    Loterie organizovaná Šarlatánem. Vyžaduje min. LOTTERY_MIN_PLAYERS účastníků.
    Šarlatán dostane XP za organizaci (flat, bez ohledu na výsledek).
    Výherce bere celý pool (vstupní poplatky všech).
    """
    __tablename__ = "lotteries"

    id:                Mapped[int] = mapped_column(primary_key=True)
    organizer_char_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))

    entry_fee:         Mapped[int] = mapped_column(Integer)         # vstupní poplatek
    pool_total:        Mapped[int] = mapped_column(Integer, default=0)

    status:            Mapped[str] = mapped_column(String(16), default="open")
    # open | drawing | completed | cancelled (zrušena pokud < MIN_PLAYERS před draw)

    winner_char_id:    Mapped[int | None]      = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)
    created_at:        Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    draw_at:           Mapped[datetime | None] = mapped_column(DateTime, nullable=True)    # plánované losování
    drawn_at:          Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    xp_awarded:        Mapped[bool] = mapped_column(Boolean, default=False)

    organizer = relationship("Character", foreign_keys=[organizer_char_id])
    winner    = relationship("Character", foreign_keys=[winner_char_id])
    entries   = relationship("LotteryEntry", back_populates="lottery", cascade="all, delete-orphan")

    @property
    def entry_count(self) -> int:
        return len(self.entries) if self.entries else 0

    @property
    def can_draw(self) -> bool:
        return self.status == "open" and self.entry_count >= LOTTERY_MIN_PLAYERS

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "organizer":    self.organizer.name if self.organizer else "?",
            "entry_fee":    self.entry_fee,
            "pool_total":   self.pool_total,
            "entry_count":  self.entry_count,
            "status":       self.status,
            "winner":       self.winner.name if self.winner else None,
            "created_at":   self.created_at.isoformat(),
            "draw_at":      self.draw_at.isoformat() if self.draw_at else None,
        }


class LotteryEntry(Base):
    """Jeden účastník loterie. Hráč může mít max 1 vstup per loterie."""
    __tablename__ = "lottery_entries"

    id:           Mapped[int]      = mapped_column(primary_key=True)
    lottery_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("lotteries.id"))
    character_id: Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))
    entered_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lottery   = relationship("Lottery", back_populates="entries")
    character = relationship("Character")

    def to_dict(self) -> dict:
        return {
            "character": self.character.name if self.character else "?",
            "entered_at": self.entered_at.isoformat(),
        }
