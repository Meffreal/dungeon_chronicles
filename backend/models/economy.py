"""
models/economy.py — Economy audit log

GoldTransaction zaznamenává každou změnu gold postavy:
  amount > 0  = příjem (quest reward, boss odměna, prodej...)
  amount < 0  = výdaj (nákup, poplatek, sázka...)

Použití (v routerech, VŽDY PO úpravě char.gold):
    char.gold += quest.reward_gold
    await log_gold(db, char, quest.reward_gold, GoldReason.QUEST_REWARD)
"""

import enum
import json
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class GoldReason(str, enum.Enum):
    """Důvod změny gold — použij jako `reason` v log_gold()."""
    QUEST_REWARD        = "quest_reward"
    SHOP_PURCHASE       = "shop_purchase"
    MARKET_BUY          = "market_buy"
    MARKET_SELL         = "market_sell"
    INVENTORY_SELL      = "inventory_sell"
    ARENA_REWARD        = "arena_reward"
    ARENA_SEASON_REWARD = "arena_season_reward"
    BOSS_REWARD         = "boss_reward"
    DUNGEON_REWARD      = "dungeon_reward"
    GUILD_CREATE        = "guild_create"
    GUILD_BOSS_REWARD   = "guild_boss_reward"
    FACTION_REWARD      = "faction_reward"
    PROFESSION_LEARN    = "profession_learn"
    DIVINER_PURCHASE    = "diviner_purchase"
    DIVINER_SALE        = "diviner_sale"
    GAMBLER_BET         = "gambler_bet"
    GAMBLER_LOTTERY     = "gambler_lottery"
    GAMBLER_WIN         = "gambler_win"
    GAMBLER_REFUND      = "gambler_refund"
    TRANSMOG_FEE        = "transmog_fee"
    REPAIR_FEE          = "repair_fee"
    RESPEC_FEE          = "respec_fee"


class GoldTransaction(Base):
    """Audit záznam každé změny gold postavy."""
    __tablename__ = "gold_transactions"

    id:            Mapped[int]          = mapped_column(primary_key=True)
    character_id:  Mapped[int]          = mapped_column(Integer, ForeignKey("characters.id", ondelete="CASCADE"))
    amount:        Mapped[int]          = mapped_column(Integer)          # kladné = příjem, záporné = výdaj
    reason:        Mapped[str]          = mapped_column(String(32))       # GoldReason value
    balance_after: Mapped[int]          = mapped_column(Integer)          # char.gold po transakci
    timestamp:     Mapped[datetime]     = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    detail:        Mapped[str | None]   = mapped_column(Text, nullable=True)  # JSON kontext (volitelné)

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "character_id":  self.character_id,
            "amount":        self.amount,
            "reason":        self.reason,
            "balance_after": self.balance_after,
            "timestamp":     self.timestamp.isoformat() if self.timestamp else None,
            "detail":        json.loads(self.detail) if self.detail else None,
        }


async def log_gold(
    db,
    char,
    amount: int,
    reason: "GoldReason | str",
    detail: dict | None = None,
) -> GoldTransaction:
    """
    Zaloguj změnu gold pro danou postavu.

    VŽDY volat PO úpravě char.gold — `balance_after` čte aktuální char.gold.

    Args:
        db:      AsyncSession
        char:    Character instance (s již aktualizovaným char.gold)
        amount:  změna (+příjem / -výdaj) — stejná hodnota co byla přičtena/odečtena
        reason:  GoldReason enum nebo string
        detail:  volitelný dict s extra kontextem (quest_id, item_name, ...)
    """
    tx = GoldTransaction(
        character_id=char.id,
        amount=amount,
        reason=str(reason.value if isinstance(reason, GoldReason) else reason),
        balance_after=char.gold,
        detail=json.dumps(detail, default=str) if detail else None,
    )
    db.add(tx)
    return tx
