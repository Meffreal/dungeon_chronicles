"""
models/arena.py — Historie aréna zápasů + Sezóny
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import Integer, ForeignKey, Boolean, Text, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

SEASON_DURATION_DAYS = 14   # délka sezóny

# Odměny (gold) podle finálního pořadí
SEASON_REWARDS = [
    (1,   1,  5000),   # rank 1
    (2,   3,  3000),   # rank 2–3
    (4,  10,  1500),   # rank 4–10
    (11, 25,   500),   # rank 11–25
    (26, 999,  100),   # účast (alespoň 1 zápas)
]

# Exkluzivní kosmetické odměny (titul + portrait frame) podle finálního pořadí
# (rank_low, rank_high, title, frame_key)
SEASON_COSMETIC_REWARDS = [
    (1,   1,  "Arena Grand Champion", "season-champion"),    # animovaný zlatý frame
    (2,   3,  "Arena Champion",       "season-challenger"),  # animovaný stříbrný frame
    (4,  10,  "Arena Veteran",        "season-veteran"),     # bronzový glow frame
    (11, 25,  "Arena Contender",      None),                 # jen titul, bez frame
    (26, 999, None,                   None),                 # jen gold, bez kosmetik
]


def get_season_reward(rank: int) -> int:
    for low, high, gold in SEASON_REWARDS:
        if low <= rank <= high:
            return gold
    return 0


def get_season_cosmetics(rank: int) -> tuple[str | None, str | None]:
    """Vrátí (title, frame_key) pro daný finální rank. None = žádná odměna."""
    for low, high, title, frame in SEASON_COSMETIC_REWARDS:
        if low <= rank <= high:
            return title, frame
    return None, None


class Season(Base):
    __tablename__ = "seasons"

    id:         Mapped[int]      = mapped_column(primary_key=True)
    number:     Mapped[int]      = mapped_column(Integer, unique=True)
    start_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_at:     Mapped[datetime] = mapped_column(DateTime)
    is_active:  Mapped[bool]     = mapped_column(Boolean, default=True)
    theme_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    theme_lore: Mapped[str | None] = mapped_column(Text, nullable=True)

    results = relationship("SeasonResult", back_populates="season")

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc).replace(tzinfo=None) >= self.end_at

    @property
    def days_remaining(self) -> int:
        delta = self.end_at - datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0, delta.days)

    @property
    def hours_remaining(self) -> int:
        delta = self.end_at - datetime.now(timezone.utc).replace(tzinfo=None)
        total_seconds = max(0, int(delta.total_seconds()))
        return total_seconds // 3600

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "number":         self.number,
            "start_at":       self.start_at.isoformat(),
            "end_at":         self.end_at.isoformat(),
            "is_active":      self.is_active,
            "is_expired":     self.is_expired,
            "days_remaining": self.days_remaining,
            "hours_remaining": self.hours_remaining,
            "theme_name":     self.theme_name,
            "theme_lore":     self.theme_lore,
        }


class SeasonResult(Base):
    __tablename__ = "season_results"

    id:             Mapped[int]      = mapped_column(primary_key=True)
    season_id:      Mapped[int]      = mapped_column(Integer, ForeignKey("seasons.id"))
    character_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))
    final_rank:     Mapped[int]      = mapped_column(Integer)
    final_elo:      Mapped[int]      = mapped_column(Integer)
    reward_gold:    Mapped[int]      = mapped_column(Integer, default=0)
    reward_claimed: Mapped[bool]     = mapped_column(Boolean, default=False)
    # Exkluzivní kosmetické odměny za sezónu (přiřadí se při process_expired_season)
    reward_title:   Mapped[str|None] = mapped_column(String(64), nullable=True)
    reward_frame:   Mapped[str|None] = mapped_column(String(32), nullable=True)
    # Příznak zda hráč již viděl sezónní recap modal
    recap_shown:    Mapped[bool]     = mapped_column(Boolean, default=False)

    season    = relationship("Season", back_populates="results")
    character = relationship("Character")

    def to_dict(self) -> dict:
        return {
            "season_id":      self.season_id,
            "character":      self.character.name if self.character else "?",
            "final_rank":     self.final_rank,
            "final_elo":      self.final_elo,
            "reward_gold":    self.reward_gold,
            "reward_claimed": self.reward_claimed,
            "reward_title":   self.reward_title,
            "reward_frame":   self.reward_frame,
        }



class ArenaMatch(Base):
    __tablename__ = "arena_matches"

    id:           Mapped[int]  = mapped_column(primary_key=True)
    attacker_id:  Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"))
    defender_id:  Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"))
    winner_id:    Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"))
    attacker_elo_change: Mapped[int] = mapped_column(Integer, default=0)
    defender_elo_change: Mapped[int] = mapped_column(Integer, default=0)
    battle_log:   Mapped[str]  = mapped_column(Text, default="")
    played_at:    Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    attacker = relationship("Character", foreign_keys=[attacker_id])
    defender = relationship("Character", foreign_keys=[defender_id])
    winner   = relationship("Character", foreign_keys=[winner_id])

    def to_dict(self, pov_char_id: int | None = None) -> dict:
        won = (self.winner_id == pov_char_id) if pov_char_id else None
        elo_change = 0
        if pov_char_id == self.attacker_id:
            elo_change = self.attacker_elo_change
        elif pov_char_id == self.defender_id:
            elo_change = self.defender_elo_change

        return {
            "id":           self.id,
            "attacker":     self.attacker.name if self.attacker else "?",
            "attacker_id":  self.attacker_id,
            "defender":     self.defender.name if self.defender else "?",
            "defender_id":  self.defender_id,
            "winner":       self.winner.name if self.winner else "?",
            "winner_id":    self.winner_id,
            "won":          won,
            "elo_change":   elo_change,
            "attacker_elo_change": self.attacker_elo_change,
            "defender_elo_change": self.defender_elo_change,
            "battle_log":   self.battle_log,
            "played_at":    self.played_at.isoformat(),
        }
