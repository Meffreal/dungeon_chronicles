"""
models/bloodline.py — Bloodline meta-progression (per user)
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Bloodline(Base):
    __tablename__ = "bloodlines"

    id:           Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    user_id:      Mapped[int]            = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    total_xp:     Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    level:        Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    unlocks_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)
    updated_at:   Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id":       self.id,
            "user_id":  self.user_id,
            "total_xp": self.total_xp,
            "level":    self.level,
            "unlocks":  self.unlocks_json or {},
        }
