"""
models/item.py — Itemy, rarity, stats
"""
import enum
from typing import Optional
from sqlalchemy import String, Integer, Text, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Rarity(str, enum.Enum):
    COMMON    = "common"
    UNCOMMON  = "uncommon"
    RARE      = "rare"
    EPIC      = "epic"
    LEGENDARY = "legendary"
    SET       = "set"

RARITY_COLOR = {
    Rarity.COMMON:    "#9d9d9d",
    Rarity.UNCOMMON:  "#1eff00",
    Rarity.RARE:      "#0070dd",
    Rarity.EPIC:      "#a335ee",
    Rarity.LEGENDARY: "#ff8000",
    Rarity.SET:       "#00d4ff",
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

    # Setové itemy
    set_id:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    set_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def to_dict(self) -> dict:
        try:
            rarity_obj = Rarity(self.rarity)
        except ValueError:
            rarity_obj = self.rarity  # fallback pro neznámé hodnoty
        return {
            "id": self.id,
            "name": self.name,
            "type": self.item_type,
            "rarity": self.rarity,
            "rarity_color": RARITY_COLOR.get(rarity_obj, "#fff"),
            "set_id":   self.set_id,
            "set_name": self.set_name,
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


# ── Gear upgrade systém ───────────────────────────────────────────────────────
UPGRADE_COSTS = {0: 500, 1: 2_000, 2: 8_000}  # gold pro přechod level → level+1
UPGRADE_STAT_MULT   = [1.0, 1.35, 1.80, 2.40]  # kumulativní mult pro úroveň 0–3
UPGRADE_RARITY_CHAIN = ["common", "uncommon", "rare", "epic"]
UPGRADEABLE_RARITIES = {"common", "uncommon", "rare"}  # epic/legendary/set nelze
MAX_UPGRADE_LEVEL = 3

UPGRADE_TIER_ICON = ["", "★", "★★", "★★★"]  # display badge


class InventoryItem(Base):
    __tablename__ = "inventory"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, __import__('sqlalchemy').ForeignKey("characters.id"))
    item_id:      Mapped[int] = mapped_column(Integer, __import__('sqlalchemy').ForeignKey("items.id"))
    quantity:     Mapped[int] = mapped_column(Integer, default=1)
    upgrade_level: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    durability:   Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    legacy_chain_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Legacy systém: item čekající na příštího hrdinu
    is_legacy_pending:    Mapped[Optional[bool]] = mapped_column(__import__('sqlalchemy').Boolean, nullable=True, default=False)
    legacy_owner_user_id: Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)

    character = relationship("Character", back_populates="inventory")
    item      = relationship("Item")

    def _upgraded_item_dict(self) -> dict | None:
        """Vrátí item.to_dict() s aplikovanými upgrade bonusy a posunutou raritou."""
        if not self.item:
            return None
        d = self.item.to_dict()
        ul = self.upgrade_level or 0
        if ul > 0:
            mult = UPGRADE_STAT_MULT[min(ul, MAX_UPGRADE_LEVEL)]
            # Zvyš pouze přímé combat bonusy (ne primary stat bonusy — ty by se kumulovaly)
            for bk in ("atk", "def", "spd", "hp", "mp"):
                if d["bonuses"][bk]:
                    d["bonuses"][bk] = max(1, int(d["bonuses"][bk] * mult))
            # Posunutá rarity pro zobrazení
            base_idx = UPGRADE_RARITY_CHAIN.index(d["rarity"]) if d["rarity"] in UPGRADE_RARITY_CHAIN else 0
            new_idx = min(base_idx + ul, len(UPGRADE_RARITY_CHAIN) - 1)
            new_rarity = UPGRADE_RARITY_CHAIN[new_idx]
            d["rarity"] = new_rarity
            d["rarity_color"] = RARITY_COLOR.get(Rarity(new_rarity), "#fff")
        d["upgrade_level"] = ul
        return d

    def to_dict(self) -> dict:
        dur = self.durability if self.durability is not None else 100
        return {
            "id":            self.id,
            "item":          self._upgraded_item_dict(),
            "quantity":      self.quantity,
            "upgrade_level": self.upgrade_level or 0,
            "durability":    dur,
        }
