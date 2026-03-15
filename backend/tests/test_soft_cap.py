"""
tests/test_soft_cap.py — Unit testy pro soft_cap_stat (diminishing returns)

Zóny:
  0–50  : 100 % return (lineární)
  51–150: 50 + 70 % of (value − 50)
  151+  : 50 + 70 + 30 % of (value − 150)
"""
import pytest
from game.combat_engine import soft_cap_stat


# ── Zóna 1 — lineární (0–50) ──────────────────────────────────────────────────

def test_zone1_zero():
    assert soft_cap_stat(0) == 0


def test_zone1_one():
    assert soft_cap_stat(1) == 1


def test_zone1_mid():
    assert soft_cap_stat(25) == 25


def test_zone1_boundary():
    assert soft_cap_stat(50) == 50


def test_zone1_all_linear():
    """V zóně 1 (0–50) musí výstup přesně odpovídat vstupu."""
    for v in range(0, 51):
        assert soft_cap_stat(v) == v, f"soft_cap_stat({v}) != {v}"


# ── Zóna 2 — 70 % (51–150) ────────────────────────────────────────────────────

def test_zone2_value_100():
    # 50 + int((100 − 50) * 0.70) = 50 + 35 = 85
    assert soft_cap_stat(100) == 85


def test_zone2_value_80():
    # 50 + int((80 − 50) * 0.70) = 50 + 21 = 71
    assert soft_cap_stat(80) == 71


def test_zone2_boundary_150():
    # 50 + int((150 − 50) * 0.70) = 50 + 70 = 120
    assert soft_cap_stat(150) == 120


def test_zone2_always_less_than_raw():
    """Ve zóně 2 musí být výstup vždy menší než vstup."""
    for v in range(51, 151):
        assert soft_cap_stat(v) < v, f"soft_cap_stat({v}) >= {v}"


# ── Zóna 3 — 30 % (151+) ──────────────────────────────────────────────────────

def test_zone3_value_200():
    # 50 + 70 + int((200 − 150) * 0.30) = 120 + 15 = 135
    assert soft_cap_stat(200) == 135


def test_zone3_value_300():
    # 50 + 70 + int((300 − 150) * 0.30) = 120 + 45 = 165
    assert soft_cap_stat(300) == 165


def test_zone3_value_500():
    # 50 + 70 + int((500 − 150) * 0.30) = 120 + 105 = 225
    assert soft_cap_stat(500) == 225


def test_zone3_always_less_than_raw():
    """Ve zóně 3 musí být výstup vždy menší než vstup."""
    for v in range(151, 601, 10):
        assert soft_cap_stat(v) < v, f"soft_cap_stat({v}) >= {v}"


# ── Monotónnost ────────────────────────────────────────────────────────────────

def test_monotone_increasing():
    """Vyšší vstup vždy dá vyšší nebo stejný výstup (funkce je neklesající)."""
    prev = soft_cap_stat(0)
    for v in range(1, 501):
        cur = soft_cap_stat(v)
        assert cur >= prev, f"soft_cap_stat({v}) < soft_cap_stat({v - 1})"
        prev = cur


# ── Přechody mezi zónami ───────────────────────────────────────────────────────

def test_boundary_zone1_to_zone2():
    """Přechod 50 → 51 musí být hladký (žádný skok dolů)."""
    assert soft_cap_stat(51) >= soft_cap_stat(50)


def test_boundary_zone2_to_zone3():
    """Přechod 150 → 151 musí být hladký."""
    assert soft_cap_stat(151) >= soft_cap_stat(150)
