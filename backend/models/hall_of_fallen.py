"""
models/hall_of_fallen.py — Permanentní Hall of the Fallen záznam
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class HallOfFallen(Base):
    __tablename__ = "hall_of_fallen"

    id:            Mapped[int]             = mapped_column(Integer, primary_key=True, index=True)
    user_id:       Mapped[int]             = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    character_id:  Mapped[int]             = mapped_column(Integer, nullable=False)  # historický, bez FK (char smazán)

    # Snapshot postavy při smrti
    hero_name:     Mapped[str]             = mapped_column(String(64), nullable=False)
    hero_cls:      Mapped[str]             = mapped_column(String(32), nullable=False)
    hero_level:    Mapped[int]             = mapped_column(Integer, nullable=False)
    hero_faction:  Mapped[Optional[str]]   = mapped_column(String(64), nullable=True)

    # Smrt
    killed_by:     Mapped[Optional[str]]   = mapped_column(String(255), nullable=True)
    death_dungeon: Mapped[Optional[str]]   = mapped_column(String(255), nullable=True)
    died_at:       Mapped[datetime]        = mapped_column(DateTime, nullable=False)
    days_survived: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    dungeons_cleared: Mapped[int]          = mapped_column(Integer, default=0, nullable=False)

    # Extra data (talenty, subclass atd.)
    build_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Epitaf (volitelný hráčem)
    epitaph:       Mapped[Optional[str]]   = mapped_column(String(280), nullable=True)

    recorded_at:   Mapped[datetime]        = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "hero_name":        self.hero_name,
            "hero_cls":         self.hero_cls,
            "hero_level":       self.hero_level,
            "hero_faction":     self.hero_faction,
            "killed_by":        self.killed_by,
            "death_dungeon":    self.death_dungeon,
            "died_at":          self.died_at.isoformat() if self.died_at else None,
            "days_survived":    self.days_survived,
            "dungeons_cleared": self.dungeons_cleared,
            "epitaph":          self.epitaph,
            "build_snapshot":   self.build_snapshot or {},
        }
