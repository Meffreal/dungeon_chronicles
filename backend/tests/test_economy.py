"""
tests/test_economy.py — Unit testy pro economy systém

Testuje:
  - GoldReason enum — hodnoty, unikátnost
  - GoldTransaction.to_dict() — serializace
  - log_gold() — vytvoření transakce, reason jako enum/string, detail JSON
  - Quest reward scaling formula: int(base * (1 + level * 0.1))
  - Market listing fee formula: max(50, int(price * 0.05))
"""
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from models.economy import GoldReason, GoldTransaction, log_gold


# ══════════════════════════════════════════════════════════════════════════════
# GoldReason enum
# ══════════════════════════════════════════════════════════════════════════════

def test_gold_reason_is_str_enum():
    """GoldReason je str enum — hodnoty jsou stringy."""
    for reason in GoldReason:
        assert isinstance(reason.value, str)
        assert isinstance(reason, str)  # str enum


def test_gold_reason_values_are_unique():
    """Každá GoldReason hodnota musí být unikátní."""
    values = [r.value for r in GoldReason]
    assert len(values) == len(set(values)), "Duplikátní hodnoty v GoldReason!"


def test_gold_reason_quest_reward():
    assert GoldReason.QUEST_REWARD == "quest_reward"


def test_gold_reason_shop_purchase():
    assert GoldReason.SHOP_PURCHASE == "shop_purchase"


def test_gold_reason_market_buy():
    assert GoldReason.MARKET_BUY == "market_buy"


def test_gold_reason_market_sell():
    assert GoldReason.MARKET_SELL == "market_sell"


def test_gold_reason_arena_reward():
    assert GoldReason.ARENA_REWARD == "arena_reward"


def test_gold_reason_boss_reward():
    assert GoldReason.BOSS_REWARD == "boss_reward"


def test_gold_reason_dungeon_reward():
    assert GoldReason.DUNGEON_REWARD == "dungeon_reward"


def test_gold_reason_transmog_fee_exists():
    """TRANSMOG_FEE přidán v [3.6]."""
    assert GoldReason.TRANSMOG_FEE == "transmog_fee"


def test_gold_reason_repair_fee_exists():
    """REPAIR_FEE přidán v [3.6]."""
    assert GoldReason.REPAIR_FEE == "repair_fee"


def test_gold_reason_count_at_least_20():
    """Musí existovat aspoň 20 důvodů (pokrytí celé ekonomiky)."""
    assert len(list(GoldReason)) >= 20


# ══════════════════════════════════════════════════════════════════════════════
# GoldTransaction.to_dict()
# ══════════════════════════════════════════════════════════════════════════════

def test_to_dict_basic_fields():
    tx = GoldTransaction(
        id=1, character_id=42, amount=100,
        reason="quest_reward", balance_after=500,
        timestamp=datetime(2026, 2, 28, 12, 0, 0),
        detail=None,
    )
    d = tx.to_dict()
    assert d["id"]            == 1
    assert d["character_id"]  == 42
    assert d["amount"]        == 100
    assert d["reason"]        == "quest_reward"
    assert d["balance_after"] == 500
    assert d["detail"]        is None
    assert "timestamp" in d


def test_to_dict_timestamp_is_string():
    tx = GoldTransaction(
        id=1, character_id=1, amount=10, reason="quest_reward",
        balance_after=100, timestamp=datetime(2026, 2, 28), detail=None,
    )
    d = tx.to_dict()
    assert isinstance(d["timestamp"], str)


def test_to_dict_with_detail():
    """Detail se vrátí jako parsovaný dict, ne string."""
    detail = {"quest_id": 5, "quest_name": "Skřeti"}
    tx = GoldTransaction(
        id=2, character_id=1, amount=-50, reason="shop_purchase",
        balance_after=450, timestamp=datetime(2026, 2, 28),
        detail=json.dumps(detail),
    )
    d = tx.to_dict()
    assert d["detail"] == detail


def test_to_dict_negative_amount():
    """Záporný amount (výdaj) se správně vrátí."""
    tx = GoldTransaction(
        id=3, character_id=1, amount=-200, reason="market_buy",
        balance_after=800, timestamp=datetime(2026, 2, 28), detail=None,
    )
    assert tx.to_dict()["amount"] == -200


def test_to_dict_none_timestamp():
    """Timestamp None vrátí None (ne výjimku)."""
    tx = GoldTransaction(
        id=4, character_id=1, amount=10, reason="quest_reward",
        balance_after=100, timestamp=None, detail=None,
    )
    d = tx.to_dict()
    assert d["timestamp"] is None


# ══════════════════════════════════════════════════════════════════════════════
# log_gold() — async, s mock DB
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_log_gold_creates_transaction():
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 7
    char.gold = 1000

    tx = await log_gold(db, char, 200, GoldReason.QUEST_REWARD)

    assert tx.character_id  == 7
    assert tx.amount        == 200
    assert tx.reason        == "quest_reward"
    assert tx.balance_after == 1000
    assert tx.detail        is None
    db.add.assert_called_once_with(tx)


@pytest.mark.asyncio
async def test_log_gold_negative_amount():
    """Záporný amount (výdaj) se uloží správně."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 800

    tx = await log_gold(db, char, -200, GoldReason.SHOP_PURCHASE)
    assert tx.amount        == -200
    assert tx.balance_after == 800


@pytest.mark.asyncio
async def test_log_gold_with_detail_dict():
    """Detail dict se uloží jako JSON string."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 500

    detail = {"item_id": 99, "item_name": "Legendární meč"}
    tx = await log_gold(db, char, -100, GoldReason.SHOP_PURCHASE, detail=detail)

    assert tx.detail is not None
    assert json.loads(tx.detail) == detail


@pytest.mark.asyncio
async def test_log_gold_accepts_string_reason():
    """log_gold přijímá string jako reason (nejen GoldReason enum)."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 300

    tx = await log_gold(db, char, 100, "quest_reward")
    assert tx.reason == "quest_reward"


@pytest.mark.asyncio
async def test_log_gold_balance_after_is_current_gold():
    """balance_after musí odpovídat char.gold v okamžiku volání."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 9999  # Aktuální zůstatek

    tx = await log_gold(db, char, 500, GoldReason.BOSS_REWARD)
    assert tx.balance_after == 9999


@pytest.mark.asyncio
async def test_log_gold_enum_reason_stored_as_string():
    """GoldReason enum se uloží jako string hodnota."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 100

    tx = await log_gold(db, char, 50, GoldReason.DUNGEON_REWARD)
    assert tx.reason == "dungeon_reward"
    assert isinstance(tx.reason, str)


@pytest.mark.asyncio
async def test_log_gold_returns_transaction_instance():
    """log_gold musí vrátit GoldTransaction instanci."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 100

    tx = await log_gold(db, char, 50, GoldReason.ARENA_REWARD)
    assert isinstance(tx, GoldTransaction)


@pytest.mark.asyncio
async def test_log_gold_calls_db_add():
    """log_gold musí zavolat db.add() (ale ne db.commit())."""
    db   = AsyncMock()
    db.add = MagicMock()
    char = MagicMock()
    char.id   = 1
    char.gold = 100

    await log_gold(db, char, 50, GoldReason.GUILD_BOSS_REWARD)
    assert db.add.called
    assert not db.commit.called  # commit je na volajícím


# ══════════════════════════════════════════════════════════════════════════════
# Quest reward scaling formula
# ══════════════════════════════════════════════════════════════════════════════

def _quest_reward(base: int, level: int) -> int:
    """Formula z routers/quest.py: start_quest."""
    return int(base * (1 + level * 0.1))


def test_quest_reward_level_1():
    assert _quest_reward(100, 1) == 110


def test_quest_reward_level_5():
    assert _quest_reward(100, 5) == 150


def test_quest_reward_level_10():
    assert _quest_reward(100, 10) == 200


def test_quest_reward_level_20():
    assert _quest_reward(100, 20) == 300


def test_quest_reward_always_greater_than_base():
    """Reward musí být vždy větší nebo rovno base pro level >= 1."""
    for level in range(1, 51):
        assert _quest_reward(100, level) >= 100


def test_quest_reward_scales_monotonically():
    """Vyšší level → vyšší reward."""
    prev = _quest_reward(100, 0)
    for level in range(1, 51):
        cur = _quest_reward(100, level)
        assert cur >= prev
        prev = cur


def test_quest_reward_different_base():
    assert _quest_reward(50, 10)  == int(50  * 2.0)   # 100
    assert _quest_reward(200, 5)  == int(200 * 1.5)   # 300
    assert _quest_reward(300, 1)  == int(300 * 1.1)   # 330


# ══════════════════════════════════════════════════════════════════════════════
# Market listing fee formula
# ══════════════════════════════════════════════════════════════════════════════

LISTING_FEE_PCT = 0.05
LISTING_FEE_MIN = 50


def _listing_fee(price: int) -> int:
    """Formula z routers/market.py."""
    return max(LISTING_FEE_MIN, int(price * LISTING_FEE_PCT))


def test_listing_fee_minimum_for_cheap_item():
    """Levné předměty: fee = min 50."""
    assert _listing_fee(0)   == 50
    assert _listing_fee(100) == 50
    assert _listing_fee(500) == 50   # 500*0.05 = 25 < 50


def test_listing_fee_minimum_boundary():
    """Na hranici: fee = přesně 50."""
    assert _listing_fee(1000) == 50   # 1000*0.05 = 50.0 = 50


def test_listing_fee_percentage_above_min():
    """Drahé předměty: fee = 5 % ceny."""
    assert _listing_fee(1001) == 50    # int(1001*0.05) = 50 (stále min)
    assert _listing_fee(1100) == 55    # int(1100*0.05) = 55
    assert _listing_fee(2000) == 100   # int(2000*0.05) = 100
    assert _listing_fee(10000) == 500  # int(10000*0.05) = 500


def test_listing_fee_never_below_minimum():
    """Fee nesmí být nikdy nižší než LISTING_FEE_MIN."""
    for price in [0, 10, 50, 100, 500, 999, 1000, 1001, 5000, 100000]:
        assert _listing_fee(price) >= LISTING_FEE_MIN


def test_listing_fee_monotone():
    """Vyšší cena → vyšší nebo stejná fee."""
    prev = _listing_fee(0)
    for price in range(0, 10001, 100):
        cur = _listing_fee(price)
        assert cur >= prev
        prev = cur
