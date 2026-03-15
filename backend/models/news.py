"""
models/news.py — In-game news feed / patch notes
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class GameNews(Base):
    __tablename__ = "game_news"

    id:           Mapped[int]          = mapped_column(primary_key=True)
    title:        Mapped[str]          = mapped_column(String(120))
    body:         Mapped[str]          = mapped_column(Text)
    news_type:    Mapped[str]          = mapped_column(String(20), default="info")
    # info | event | maintenance | balance | hotfix
    published_at: Mapped[datetime]     = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    expires_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active:    Mapped[bool]         = mapped_column(Boolean, default=True)
    author:       Mapped[str | None]   = mapped_column(String(64), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "title":        self.title,
            "body":         self.body,
            "news_type":    self.news_type,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "expires_at":   self.expires_at.isoformat() if self.expires_at else None,
            "is_active":    self.is_active,
            "author":       self.author,
        }
