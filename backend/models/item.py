"""
models/item.py — Itemy, rarity, stats
"""
import enum
from sqlalchemy import String, Integer, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Rarity(str, enum.Enum):
    COMMON    = "common"
    UNCOMMON  = "uncommon"
    RARE      = "rare"
    EPIC      = "epic"
    LEGENDARY = "legendary"

RARITY_COLOR = {
    Rarity.COMMON:    "#9d9d9d",
    Rarity.UNCOMMON:  "#1eff00",
    Rarity.RARE:      "#0070dd",
    Rarity.EPIC:      "#a335ee",
    Rarity.LEGENDARY: "#ff8000",
}

class ItemType(str, enum.Enum):
    WEAPON  = "weapon"
    HELMET  = "helmet"
    ARMOR   = "armor"
    GLOVES  = "gloves"
    BOOTS   = "boots"
    RING    = "ring"
    AMULET  = "amulet"
    POTION  = "potion"

class Item(Base):
    __tablename__ = "items"

    id:          Mapped[int] = mapped_column(primary_key=True)
    name:        Mapped[str] = mapped_column(String(64), unique=True)
    item_type:   Mapped[str] = mapped_column(String(16))
    rarity:      Mapped[str] = mapped_column(String(16), default=Rarity.COMMON)
    description: Mapped[str] = mapped_column(Text, default="")
    icon:        Mapped[str] = mapped_column(String(8), default="⚔️")  # emoji

    # Bonusy
    bonus_atk:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_def:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_spd:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_hp:   Mapped[int] = mapped_column(Integer, default=0)
    bonus_mp:   Mapped[int] = mapped_column(Integer, default=0)
    bonus_str:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_dex:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_int:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_end:  Mapped[int] = mapped_column(Integer, default=0)
    bonus_luck: Mapped[int] = mapped_column(Integer, default=0)

    min_level:  Mapped[int] = mapped_column(Integer, default=1)
    sell_price: Mapped[int] = mapped_column(Integer, default=10)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.item_type,
            "rarity": self.rarity,
            "rarity_color": RARITY_COLOR.get(Rarity(self.rarity), "#fff"),
            "description": self.description,
            "icon": self.icon,
            "bonuses": {
                "atk": self.bonus_atk, "def": self.bonus_def,
                "spd": self.bonus_spd, "hp":  self.bonus_hp,
                "mp":  self.bonus_mp,  "str": self.bonus_str,
                "dex": self.bonus_dex, "int": self.bonus_int,
                "end": self.bonus_end, "luck":self.bonus_luck,
            },
            "min_level": self.min_level,
            "sell_price": self.sell_price,
        }


class InventoryItem(Base):
    __tablename__ = "inventory"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, __import__('sqlalchemy').ForeignKey("characters.id"))
    item_id:      Mapped[int] = mapped_column(Integer, __import__('sqlalchemy').ForeignKey("items.id"))
    quantity:     Mapped[int] = mapped_column(Integer, default=1)

    character = relationship("Character", back_populates="inventory")
    item      = relationship("Item")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item": self.item.to_dict() if self.item else None,
            "quantity": self.quantity,
        }
