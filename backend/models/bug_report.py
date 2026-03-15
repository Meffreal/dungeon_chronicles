"""
models/bug_report.py — Bug reports od hráčů
"""
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class BugReport(Base):
    __tablename__ = "bug_reports"

    id:           Mapped[int]          = mapped_column(primary_key=True)
    character_id: Mapped[int | None]   = mapped_column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
    title:        Mapped[str]          = mapped_column(String(120))
    description:  Mapped[str]          = mapped_column(Text)
    steps:        Mapped[str | None]   = mapped_column(Text, nullable=True)
    severity:     Mapped[str]          = mapped_column(String(20), default="minor")
    # cosmetic | minor | critical
    page_context: Mapped[str | None]   = mapped_column(String(80), nullable=True)
    status:       Mapped[str]          = mapped_column(String(20), default="open")
    # open | in_progress | resolved | closed
    char_name:    Mapped[str | None]   = mapped_column(String(80), nullable=True)
    char_level:   Mapped[int | None]   = mapped_column(Integer, nullable=True)
    char_class:   Mapped[str | None]   = mapped_column(String(60), nullable=True)
    admin_note:   Mapped[str | None]   = mapped_column(Text, nullable=True)
    created_at:   Mapped[datetime]     = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at:   Mapped[datetime]     = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "character_id": self.character_id,
            "title":        self.title,
            "description":  self.description,
            "steps":        self.steps,
            "severity":     self.severity,
            "page_context": self.page_context,
            "status":       self.status,
            "char_name":    self.char_name,
            "char_level":   self.char_level,
            "char_class":   self.char_class,
            "admin_note":   self.admin_note,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "updated_at":   self.updated_at.isoformat() if self.updated_at else None,
        }
