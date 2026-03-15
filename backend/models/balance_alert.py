"""
models/balance_alert.py — Balance anomaly alerts pro admin monitoring.

Typy alertů:
  arena_winrate   — jedna třída má win rate > 60% v arénách
  gold_monopoly   — top 10 hráčů vlastní > 40% veškerého goldu
  gold_farm       — denní gold z arény > 3× expected cap (exploit indikátor)
  season_skew     — top hráč má 5× více wins než #2 (season skewed)
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class BalanceAlert(Base):
    __tablename__ = "balance_alerts"

    id:          Mapped[int]           = mapped_column(primary_key=True)
    alert_type:  Mapped[str]           = mapped_column(String(32), index=True)
    severity:    Mapped[str]           = mapped_column(String(16), default="warning")
    title:       Mapped[str]           = mapped_column(String(128))
    detail:      Mapped[str]           = mapped_column(Text, default="")
    detected_at: Mapped[datetime]      = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    resolved:    Mapped[bool]          = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "alert_type":  self.alert_type,
            "severity":    self.severity,
            "title":       self.title,
            "detail":      self.detail,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "resolved":    self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
