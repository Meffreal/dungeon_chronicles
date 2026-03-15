"""
models/transmog.py — Transmog systém (kosmetický vzhled vybavení).

Hráč může pro každý slot nastavit jiný item jako kosmetický vzhled.
Stats zůstávají ze skutečně nasazeného itemu — pouze vizuál se mění.
Hráč musí daný item vlastnit (mít v inventáři) a musí být stejného typu.
"""
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

TRANSMOG_COST = 100      # gold za nastavení transmogu pro jeden slot
VALID_SLOTS = {"weapon", "helmet", "armor", "gloves", "boots", "ring", "amulet"}


class TransmogSlot(Base):
    """Kosmetický vzhled pro jeden equipment slot postavy."""
    __tablename__ = "transmog_slots"

    id:               Mapped[int]           = mapped_column(primary_key=True)
    character_id:     Mapped[int]           = mapped_column(Integer, ForeignKey("characters.id"), index=True)
    slot:             Mapped[str]           = mapped_column(String(16))     # weapon / helmet / ...
    cosmetic_item_id: Mapped[int]           = mapped_column(Integer, ForeignKey("items.id"))
    applied_at:       Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    character = relationship("Character")
    cosmetic_item = relationship("Item")
