"""
models/notification.py — Herní notifikace (aréna výsledky, level up, market, atd.)
"""
import enum
from datetime import datetime
from sqlalchemy import Integer, ForeignKey, Boolean, Text, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class NotifType(str, enum.Enum):
    ARENA_WIN       = "arena_win"
    ARENA_LOSS      = "arena_loss"
    ARENA_CHALLENGE = "arena_challenge"   # byl jsi napadnut
    MARKET_SOLD     = "market_sold"       # tvůj item se prodal
    MARKET_BOUGHT   = "market_bought"     # koupil jsi item
    LEVEL_UP        = "level_up"
    QUEST_DONE      = "quest_done"
    SYSTEM          = "system"


NOTIF_ICONS = {
    NotifType.ARENA_WIN:       "🏆",
    NotifType.ARENA_LOSS:      "💀",
    NotifType.ARENA_CHALLENGE: "⚔",
    NotifType.MARKET_SOLD:     "💰",
    NotifType.MARKET_BOUGHT:   "🛒",
    NotifType.LEVEL_UP:        "⚡",
    NotifType.QUEST_DONE:      "✅",
    NotifType.SYSTEM:          "📢",
}


class Notification(Base):
    __tablename__ = "notifications"

    id:           Mapped[int]  = mapped_column(primary_key=True)
    character_id: Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"))
    type:         Mapped[str]  = mapped_column(String(32))
    title:        Mapped[str]  = mapped_column(String(128))
    body:         Mapped[str]  = mapped_column(Text, default="")
    is_read:      Mapped[bool] = mapped_column(Boolean, default=False)
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    character = relationship("Character", back_populates="notifications")

    def to_dict(self) -> dict:
        icon = NOTIF_ICONS.get(NotifType(self.type), "📢")
        return {
            "id":         self.id,
            "type":       self.type,
            "icon":       icon,
            "title":      self.title,
            "body":       self.body,
            "is_read":    self.is_read,
            "created_at": self.created_at.isoformat(),
        }
