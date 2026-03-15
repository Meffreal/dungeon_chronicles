"""
models/shop_sale.py — Sledování nákupů v NPC obchodě (rotace)
"""
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class ShopSale(Base):
    __tablename__ = "shop_sales"

    id:            Mapped[int] = mapped_column(primary_key=True)
    character_id:  Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    item_id:       Mapped[int] = mapped_column(Integer, ForeignKey("items.id"))
    rotation_slot: Mapped[int] = mapped_column(Integer)   # _current_slot() v době nákupu
