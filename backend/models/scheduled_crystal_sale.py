"""
models/scheduled_crystal_sale.py — Naplánované slevy v Crystal shopu

Admin může nastavit časově omezenou slevu na libovolnou položku z CRYSTAL_SHOP.
Sleva se automaticky aktivuje v starts_at a deaktivuje v ends_at.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class ScheduledCrystalSale(Base):
    __tablename__ = "scheduled_crystal_sales"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True)
    item_key:     Mapped[str]      = mapped_column(String(64), nullable=False)
    original_cost:Mapped[int]      = mapped_column(Integer, nullable=False)
    sale_cost:    Mapped[int]      = mapped_column(Integer, nullable=False)
    starts_at:    Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at:      Mapped[datetime] = mapped_column(DateTime, nullable=False)
    label:        Mapped[str|None] = mapped_column(String(64), nullable=True)   # "Black Friday" apod.

    def is_currently_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.utcnow()
        return self.starts_at <= now <= self.ends_at

    def to_dict(self, now: datetime | None = None) -> dict:
        now = now or datetime.utcnow()
        return {
            "id":            self.id,
            "item_key":      self.item_key,
            "original_cost": self.original_cost,
            "sale_cost":     self.sale_cost,
            "discount_pct":  round((1 - self.sale_cost / self.original_cost) * 100),
            "starts_at":     self.starts_at.isoformat(),
            "ends_at":       self.ends_at.isoformat(),
            "label":         self.label,
            "is_active":     self.is_currently_active(now),
        }
