"""
models/dungeon_modifier.py — WeeklyDungeonModifier model.

Ukládá aktuální (a historické) týdenní modifikátory dungeonů.
Vždy jeden řádek s is_active=True = aktuální týden.
Rotace je deterministická: seed = ISO year * 53 + ISO week.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from game.dungeon_modifiers import DUNGEON_MODIFIERS, MODIFIER_ROTATION


def _current_week_start() -> datetime:
    """Vrátí pondělí 00:00 UTC aktuálního týdne (bez tzinfo pro SQLite)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def _week_modifier_key(week_start: datetime) -> str:
    """Deterministicky vybere modifikátor pro daný týden dle ISO týdne."""
    iso_year, iso_week, _ = week_start.isocalendar()
    idx = (iso_year * 53 + iso_week) % len(MODIFIER_ROTATION)
    return MODIFIER_ROTATION[idx]


class WeeklyDungeonModifier(Base):
    """Týdenní dungeon modifikátor — jeden aktivní záznam."""
    __tablename__ = "weekly_dungeon_modifiers"

    id:           Mapped[int]      = mapped_column(primary_key=True)
    modifier_key: Mapped[str]      = mapped_column(String(32))
    week_start:   Mapped[datetime] = mapped_column(DateTime)
    week_end:     Mapped[datetime] = mapped_column(DateTime)
    is_active:    Mapped[bool]     = mapped_column(Boolean, default=True)

    def to_dict(self) -> dict:
        info = DUNGEON_MODIFIERS.get(self.modifier_key, {})
        return {
            "id":           self.id,
            "modifier_key": self.modifier_key,
            "name":         info.get("name",        self.modifier_key),
            "emoji":        info.get("emoji",        "❓"),
            "description":  info.get("description",  ""),
            "type":         info.get("type",          ""),
            "color":        info.get("color",         "#888"),
            "week_start":   self.week_start.isoformat(),
            "week_end":     self.week_end.isoformat(),
            "effects": {
                k: v for k, v in info.items()
                if k not in ("name", "emoji", "description", "type", "color")
            },
        }
