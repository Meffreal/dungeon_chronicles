from datetime import datetime, timezone, date
from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


def slot_count_for_level(level: int) -> int:
    return 4 if level >= 10 else 3


class QuestSlot(Base):
    __tablename__ = "quest_slots"
    __table_args__ = (UniqueConstraint("character_id", "slot_index"),)

    id:           Mapped[int]            = mapped_column(primary_key=True)
    character_id: Mapped[int]            = mapped_column(Integer, ForeignKey("characters.id"))
    slot_index:   Mapped[int]            = mapped_column(Integer)
    quest_def_id: Mapped[int]            = mapped_column(Integer)
    skip_count:   Mapped[int]            = mapped_column(Integer, default=0)
    last_skip_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime]       = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def free_skip_available(self) -> bool:
        """True pokud ještě nebylo dnes použito gratis přeskočení."""
        if self.last_skip_at is None:
            return True
        ts = self.last_skip_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.date() < date.today()

    def mark_skipped(self, paid: bool) -> None:
        self.skip_count = 0 if self.free_skip_available() else self.skip_count + 1
        self.last_skip_at = datetime.now(timezone.utc)
