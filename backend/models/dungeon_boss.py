"""
models/dungeon_boss.py — Per-character per-dungeon boss progress tracking.

One row per (character_id, dungeon_key).
Global 1h cooldown is stored on Character.dungeon_cooldown_until (added in migration 0049).
"""
import json
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class DungeonBossProgress(Base):
    """Tracks how far a character has progressed in a dungeon (boss system)."""
    __tablename__ = "dungeon_boss_progress"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), index=True)
    dungeon_key:  Mapped[str] = mapped_column(String(32))

    # Highest boss number defeated (0 = none yet)
    highest_boss_defeated: Mapped[int] = mapped_column(Integer, default=0)

    # Total lifetime boss kills in this dungeon (for stats/HoF)
    total_kills: Mapped[int] = mapped_column(Integer, default=0)

    # Last fight timestamp (for UI display)
    last_fight_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Last combat log (JSON) — stored for frontend replay
    last_combat_log_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    character = relationship("Character")

    def get_last_combat_log(self) -> list:
        if not self.last_combat_log_json:
            return []
        try:
            return json.loads(self.last_combat_log_json)
        except Exception:
            return []

    def set_last_combat_log(self, log: list, events: list) -> None:
        self.last_combat_log_json = json.dumps(
            {"log": log, "events": events}, ensure_ascii=False
        )

    def to_dict(self) -> dict:
        return {
            "dungeon_key":            self.dungeon_key,
            "highest_boss_defeated":  self.highest_boss_defeated,
            "total_kills":            self.total_kills,
            "next_boss_num":          self.highest_boss_defeated + 1,
            "last_fight_at":          self.last_fight_at.isoformat() if self.last_fight_at else None,
        }
