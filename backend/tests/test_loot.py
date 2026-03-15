"""
tests/test_loot.py — Unit testy pro drop/loot systém (game/loot.py)
Čisté testy bez DB nebo HTTP.
Statistické testy: 1000 vzorků, tolerance ±30% od očekávané hodnoty.
"""
import pytest
from game.loot import roll_drop, roll_rarity, DROP_CHANCE
from models.item import Rarity

N = 1000   # počet vzorků pro statistické testy


# ── roll_drop ─────────────────────────────────────────────────────────────────

def test_roll_drop_easy_rate():
    """Easy: ~20% drop rate."""
    hits = sum(1 for _ in range(N) if roll_drop("easy"))
    expected = DROP_CHANCE["easy"] * N   # 200
    assert expected * 0.6 <= hits <= expected * 1.4, (
        f"Easy drop rate mimo toleranci: {hits}/{N} (očekáváno ~{expected:.0f})"
    )


def test_roll_drop_normal_rate():
    """Normal: ~35% drop rate."""
    hits = sum(1 for _ in range(N) if roll_drop("normal"))
    expected = DROP_CHANCE["normal"] * N   # 350
    assert expected * 0.6 <= hits <= expected * 1.4


def test_roll_drop_boss_rate():
    """Boss: ~90% drop rate."""
    hits = sum(1 for _ in range(N) if roll_drop("boss"))
    expected = DROP_CHANCE["boss"] * N   # 900
    assert expected * 0.85 <= hits <= expected * 1.15, (
        f"Boss drop rate mimo toleranci: {hits}/{N} (očekáváno ~{expected:.0f})"
    )


def test_roll_drop_returns_bool():
    assert isinstance(roll_drop("easy"), bool)
    assert isinstance(roll_drop("boss"), bool)


# ── roll_rarity ───────────────────────────────────────────────────────────────

def test_roll_rarity_easy_mostly_common():
    """Easy: 60% common + 30% uncommon = 90% očekáváno."""
    results = [roll_rarity("easy") for _ in range(N)]
    common_uncommon = sum(1 for r in results if r in (Rarity.COMMON, Rarity.UNCOMMON))
    assert common_uncommon >= N * 0.75, (
        f"Easy rarities: {common_uncommon}/{N} common/uncommon (očekáváno ≥ 750)"
    )


def test_roll_rarity_boss_high_quality():
    """Boss: 35% epic + 15% legendary = 50% high-tier očekáváno."""
    results = [roll_rarity("boss") for _ in range(N)]
    high_tier = sum(1 for r in results if r in (Rarity.EPIC, Rarity.LEGENDARY))
    assert high_tier >= N * 0.30, (
        f"Boss rarities: {high_tier}/{N} epic/legendary (očekáváno ≥ 300)"
    )


def test_roll_rarity_returns_rarity_enum():
    rarity = roll_rarity("normal")
    assert isinstance(rarity, Rarity)


def test_roll_rarity_all_difficulties_return_valid():
    for diff in ("easy", "normal", "hard", "boss"):
        r = roll_rarity(diff)
        assert r in (Rarity.COMMON, Rarity.UNCOMMON, Rarity.RARE, Rarity.EPIC, Rarity.LEGENDARY)


def test_roll_rarity_easy_no_legendary():
    """Easy nesmí dropnout legendary (váha = 0)."""
    results = [roll_rarity("easy") for _ in range(N)]
    assert all(r != Rarity.LEGENDARY for r in results), (
        "Easy quest dropnul legendary item — to by nemělo nastat!"
    )
