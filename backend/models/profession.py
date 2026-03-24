"""
models/profession.py — Profese v3: Enchanter, Alchymista, Blacksmith
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

PROFESSION_KEYS = ["enchanter", "alchymista", "blacksmith"]

RANK_XP_THRESHOLDS = [100, 400, 1000, 2500, 5000]
RANK_NAMES = ["Novic", "Učedník", "Tovaryš", "Expert", "Mistr", "Velmistr"]
MAX_RANK = 5

PROFESSION_META = {
    "enchanter": {
        "name": "Enchanter",
        "icon": "⚗",
        "description": (
            "Vdechuješ předmětům magické vlastnosti a víš jak je zase rozložit na prach. "
            "Enchant — přidá magický efekt na item. "
            "Disenchant — rozloží item na reagenty (Arcane Dust, Enchanted Shard, Void Crystal). "
            "Rank 5: výroba Enchant Scrollů pro trh."
        ),
    },
    "alchymista": {
        "name": "Alchymista",
        "icon": "🧪",
        "description": (
            "Vaříš věci co mění průběh boje a víš jak každý lektvar rozebrat na součástky. "
            "Brew — uvaří lektvar nebo elixír. "
            "Dissolve — rozloží lektvar na reagenty (Alchemic Residue, Potent Extract, Essence Concentrate)."
        ),
    },
    "blacksmith": {
        "name": "Kovář",
        "icon": "⚒",
        "description": (
            "Ničíš aby ses znovu postavil. Na nejvyšším ranku posouváš gear za hranice legendary. "
            "Destroy — rozloží item na kovové materiály (Metal Scraps, Refined Ore, Soulsteel Fragment). "
            "Upgrade — povýší item o jeden rarity tier. Rank 5: Upgrade legendary → Soul Crafted."
        ),
    },
}


class CharacterProfession(Base):
    """Jedna profese na postavu navždy. Rank 0–5."""
    __tablename__ = "character_professions"
    __table_args__ = (UniqueConstraint("character_id"),)

    id:             Mapped[int]      = mapped_column(primary_key=True)
    character_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"), unique=True)
    profession_key: Mapped[str]      = mapped_column(String(32))
    rank:           Mapped[int]      = mapped_column(Integer, default=0)
    xp:             Mapped[int]      = mapped_column(Integer, default=0)
    chosen_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    character = relationship("Character", back_populates="professions")

    @property
    def xp_to_next_rank(self) -> int | None:
        if self.rank >= MAX_RANK:
            return None
        return RANK_XP_THRESHOLDS[self.rank]

    @property
    def rank_name(self) -> str:
        return RANK_NAMES[min(self.rank, len(RANK_NAMES) - 1)]

    def add_xp(self, amount: int) -> bool:
        if self.rank >= MAX_RANK or amount <= 0:
            return False
        self.xp += amount
        ranked_up = False
        while self.rank < MAX_RANK and self.xp >= RANK_XP_THRESHOLDS[self.rank]:
            self.xp -= RANK_XP_THRESHOLDS[self.rank]
            self.rank += 1
            ranked_up = True
        return ranked_up

    def to_dict(self) -> dict:
        meta = PROFESSION_META.get(self.profession_key, {})
        return {
            "profession_key": self.profession_key,
            "name":           meta.get("name", self.profession_key),
            "icon":           meta.get("icon", "?"),
            "description":    meta.get("description", ""),
            "rank":           self.rank,
            "rank_name":      self.rank_name,
            "xp":             self.xp,
            "xp_to_next":     self.xp_to_next_rank,
            "chosen_at":      self.chosen_at.isoformat() if self.chosen_at else None,
        }
