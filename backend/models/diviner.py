"""
models/diviner.py — Věštec: proroctví o výsledcích questů, jejich prodej a verifikace
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────

PROPHECY_EXPIRE_HOURS = 24       # svitek vyprší, pokud nebyl prodán
PROPHECY_MAX_ACTIVE   = 10       # max nevyřízených svitků najednou na jednoho Věštce

# XP hodnoty (definitivní čísla pro router/service vrstvu)
PROPHECY_XP = {
    "create":           10,    # za vytvoření svitku
    "sold":             25,    # za prodej
    "correct":         120,    # hlavní odměna – předpověď se splnila
    "wrong":             0,
    "weekly_70pct":    300,    # týdenní accuracy bonus ≥ 70 %
    "weekly_90pct":    700,    # týdenní accuracy bonus ≥ 90 %
}

# Typy predikcí
PREDICTION_TYPES = [
    "quest_success",       # předpovídá success/fail questu
    "quest_drop_rarity",   # předpovídá raritu dropu (common/uncommon/rare/epic/legendary)
    "arena_outcome",       # předpovídá vítěze arénového zápasu (zatím jen pro vlastní zápasy)
]


# ── Model ─────────────────────────────────────────────────────────────────────

class ProphecyScroll(Base):
    """
    Jeden svitek proroctví vytvořený Věštcem.
    Může být prodán na speciální Diviner burze nebo přímo hráči.
    Po dokončení cílového questu/zápasu je automaticky verifikován.
    """
    __tablename__ = "prophecy_scrolls"

    id:               Mapped[int] = mapped_column(primary_key=True)
    creator_char_id:  Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))

    # Co předpovídá
    quest_def_id:     Mapped[int | None] = mapped_column(Integer, nullable=True)     # ID questu (z quest definitions)
    prediction_type:  Mapped[str]        = mapped_column(String(32))                 # viz PREDICTION_TYPES
    prediction_value: Mapped[str]        = mapped_column(String(64))
    # Hodnoty: "success" | "fail" | "common" | "uncommon" | "rare" | "epic" | "legendary"

    # Tržní stav
    price:            Mapped[int]            = mapped_column(Integer, default=50)
    sold_to_char_id:  Mapped[int | None]     = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)
    sold_at:          Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:       Mapped[datetime] = mapped_column(DateTime)

    # Verifikace – vyplní se po dokončení cílového questu/zápasu kupujícím
    is_verified:      Mapped[bool]           = mapped_column(Boolean, default=False)
    was_correct:      Mapped[bool | None]    = mapped_column(Boolean, nullable=True)
    verified_at:      Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Zabránění dvojímu připsání XP
    xp_create_awarded:  Mapped[bool] = mapped_column(Boolean, default=False)
    xp_sold_awarded:    Mapped[bool] = mapped_column(Boolean, default=False)
    xp_result_awarded:  Mapped[bool] = mapped_column(Boolean, default=False)

    creator = relationship("Character", foreign_keys=[creator_char_id])
    buyer   = relationship("Character", foreign_keys=[sold_to_char_id])

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, creator_char_id: int, quest_def_id: int,
               prediction_type: str, prediction_value: str, price: int) -> "ProphecyScroll":
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return cls(
            creator_char_id=creator_char_id,
            quest_def_id=quest_def_id,
            prediction_type=prediction_type,
            prediction_value=prediction_value,
            price=price,
            expires_at=now + timedelta(hours=PROPHECY_EXPIRE_HOURS),
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_sold(self) -> bool:
        return self.sold_to_char_id is not None

    @property
    def is_expired(self) -> bool:
        exp = self.expires_at.replace(tzinfo=None) if self.expires_at.tzinfo else self.expires_at
        return datetime.now(timezone.utc).replace(tzinfo=None) > exp

    @property
    def is_available(self) -> bool:
        """Svitek lze koupit."""
        return not self.is_sold and not self.is_expired and not self.is_verified

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self, for_buyer: bool = False) -> dict:
        base = {
            "id":               self.id,
            "creator":          self.creator.name if self.creator else "?",
            "quest_def_id":     self.quest_def_id,
            "prediction_type":  self.prediction_type,
            "price":            self.price,
            "is_sold":          self.is_sold,
            "is_expired":       self.is_expired,
            "created_at":       self.created_at.isoformat(),
            "expires_at":       self.expires_at.isoformat(),
            "is_verified":      self.is_verified,
            "was_correct":      self.was_correct,
        }
        # Kupující vidí konkrétní předpověď jen po nákupu
        if for_buyer or self.is_sold:
            base["prediction_value"] = self.prediction_value
        return base
