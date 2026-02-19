"""
models/market.py — Hráčský trh
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

MARKET_FEE = 0.05        # 5% poplatek při prodeji
LISTING_HOURS = 48       # listing expiruje po 48h

class MarketListing(Base):
    __tablename__ = "market_listings"

    id:           Mapped[int]  = mapped_column(primary_key=True)
    seller_id:    Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"))
    item_id:      Mapped[int]  = mapped_column(Integer, ForeignKey("items.id"))
    quantity:     Mapped[int]  = mapped_column(Integer, default=1)
    price:        Mapped[int]  = mapped_column(Integer)           # cena za kus
    listed_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_sold:      Mapped[bool] = mapped_column(Boolean, default=False)
    buyer_id:     Mapped[int | None] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)

    seller = relationship("Character", foreign_keys=[seller_id])
    buyer  = relationship("Character", foreign_keys=[buyer_id])
    item   = relationship("Item")

    @classmethod
    def create(cls, seller_id: int, item_id: int, quantity: int, price: int):
        return cls(
            seller_id=seller_id,
            item_id=item_id,
            quantity=quantity,
            price=price,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=LISTING_HOURS),
        )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "seller":      self.seller.name if self.seller else "?",
            "item":        self.item.to_dict() if self.item else None,
            "quantity":    self.quantity,
            "price":       self.price,
            "total":       self.price * self.quantity,
            "listed_at":   self.listed_at.isoformat(),
            "expires_at":  self.expires_at.isoformat(),
            "is_expired":  self.is_expired,
        }
