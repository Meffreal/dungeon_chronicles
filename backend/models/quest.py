"""
models/quest.py — Questy a dungeony (time-based auto-fight)
"""
import enum
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class QuestStatus(str, enum.Enum):
    IDLE       = "idle"        # Hráč nic nehraje
    ACTIVE     = "active"      # Quest běží
    COLLECTING = "collecting"  # Hotovo, čeká na sebrání odměny

class QuestDifficulty(str, enum.Enum):
    EASY   = "easy"
    NORMAL = "normal"
    HARD   = "hard"
    BOSS   = "boss"

# ── Definice questů — načteny z config/quests.json ───────────────────────────
# Přidat nový quest = přidat řádek do backend/config/quests.json (bez deploymentu)
from game.config_loader import load_quest_definitions as _lqd
QUEST_DEFINITIONS = _lqd()

# DB-backed disabled quest set — importuj get_disabled_quest_ids() pro async přístup.
# Zachováno pro zpětnou kompatibilitu importu (_DISABLED_QUESTS) — nyní vždy prázdná,
# skutečný stav je v DB tabulce disabled_quests (viz models/disabled_quest.py).
_DISABLED_QUESTS: set[int] = set()   # Deprecated — use get_disabled_quest_ids(db)


class DailyQuestRotation(Base):
    """Denní rotace 3 questů pro každého hráče — reset v 00:00 UTC."""
    __tablename__ = "daily_quest_rotations"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), index=True)
    date:         Mapped[str] = mapped_column(String(10))   # "YYYY-MM-DD" UTC
    quest_ids:    Mapped[str] = mapped_column(Text)          # JSON "[1, 5, 13]"

    character = relationship("Character")


class Quest(Base):
    __tablename__ = "quests"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), unique=True)

    # Aktuální quest
    quest_def_id:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    status:        Mapped[str]        = mapped_column(String(16), default=QuestStatus.IDLE)
    started_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Předpočítaná odměna (vygenerovaná při startu)
    reward_xp:    Mapped[int] = mapped_column(Integer, default=0)
    reward_gold:  Mapped[int] = mapped_column(Integer, default=0)
    reward_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)

    # Výsledek boje
    success:      Mapped[bool] = mapped_column(Boolean, default=True)
    battle_log:   Mapped[str]  = mapped_column(Text, default="")  # JSON string

    # Daily quest příznak
    is_daily:     Mapped[bool] = mapped_column(Boolean, default=False)

    character   = relationship("Character", back_populates="quest")
    reward_item = relationship("Item")

    def _finish_at_aware(self):
        """Vrátí finish_at vždy jako timezone-aware datetime (SQLite ukládá naive)."""
        if self.finish_at is None:
            return None
        if self.finish_at.tzinfo is None:
            return self.finish_at.replace(tzinfo=timezone.utc)
        return self.finish_at

    @property
    def is_finished(self) -> bool:
        if self.finish_at is None:
            return False
        # Porovnávej vždy naive UTC (SQLite ignoruje timezone info)
        fa = self.finish_at.replace(tzinfo=None) if self.finish_at.tzinfo else self.finish_at
        return datetime.now(timezone.utc).replace(tzinfo=None) >= fa

    @property
    def seconds_remaining(self) -> int:
        if self.status != QuestStatus.ACTIVE or self.finish_at is None:
            return 0
        fa = self.finish_at.replace(tzinfo=None) if self.finish_at.tzinfo else self.finish_at
        remaining = (fa - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds()
        return max(0, int(remaining))

    def to_dict(self) -> dict:
        defn = next((q for q in QUEST_DEFINITIONS if q[0] == self.quest_def_id), None)
        return {
            "status": self.status,
            "quest": {
                "id":         defn[0],
                "name":       defn[1],
                "desc":       defn[2],
                "difficulty": defn[3],
                "duration":   defn[4],
                "icon":       defn[9] if len(defn) > 9 else "⚔️",
            } if defn else None,
            "started_at":       self.started_at.isoformat() if self.started_at else None,
            "finish_at":        self.finish_at.isoformat() if self.finish_at else None,
            "seconds_remaining": self.seconds_remaining,
            "is_finished":      self.is_finished,
            "reward_xp":        self.reward_xp,
            "reward_gold":      self.reward_gold,
            "reward_item":      self.reward_item.to_dict() if self.reward_item else None,
            "success":          self.success,
        }
