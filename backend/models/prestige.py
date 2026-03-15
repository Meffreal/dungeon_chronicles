"""
models/prestige.py — Prestige systém (post-level-cap)

Na level MAX_LEVEL (50) může hráč "prestige" — resetovat level na 1
a získat trvalé procentuální bonusy ke statům + krystaly + exkluzivní titul.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────
MAX_LEVEL                  = 50      # maximální level pro prestige
PRESTIGE_POWER_CAP         = 10     # max. level s bonusy ke statům

# Kumulativní bonus za každý prestige level (multiplikativní v recalculate_stats)
PRESTIGE_BONUS_ATK_PER_LVL  = 0.03  # +3 % ATK za prestige level
PRESTIGE_BONUS_DEF_PER_LVL  = 0.03  # +3 % DEF
PRESTIGE_BONUS_HP_PER_LVL   = 0.03  # +3 % HP
PRESTIGE_BONUS_MP_PER_LVL   = 0.02  # +2 % MP

# Krystalová odměna za každý prestige
PRESTIGE_CRYSTAL_REWARD = 150

# Exkluzivní tituly dle prestige levelu (nejbližší ≤ prestige_level)
PRESTIGE_TITLES: dict[int, str] = {
    1:  "Ostřílený",
    2:  "Legendární",
    3:  "Nesmrtelný",
    5:  "Polobůh",
    7:  "Transcendent",
    10: "Věčný",
    # Tituly pro post-cap (11+) — čistě kosmetické
    12: "Praostarý",
    15: "Arcivěčný",
    20: "Nadčasový",
}

# Portrait frame odměny za prestige (klíč = prestige level, hodnota = frame CSS klíč)
# Levely 1–10 každý dostane unikátní frame; nad 10 frame se nemění
PRESTIGE_FRAME_REWARDS: dict[int, str] = {
    1:  "prestige-1",
    2:  "prestige-2",
    3:  "prestige-3",
    4:  "prestige-4",
    5:  "prestige-5",
    6:  "prestige-6",
    7:  "prestige-7",
    8:  "prestige-8",
    9:  "prestige-9",
    10: "prestige-10",
}

# Třídní base primary stats (pro reset po prestige)
PRESTIGE_CLASS_BASE_STATS: dict[str, dict] = {
    "warrior": {"strength": 15, "dexterity": 8,  "intelligence": 5,  "endurance": 12, "luck": 5},
    "mage":    {"strength": 5,  "dexterity": 8,  "intelligence": 18, "endurance": 6,  "luck": 8},
    "ranger":  {"strength": 9,  "dexterity": 16, "intelligence": 8,  "endurance": 9,  "luck": 13},
}


def prestige_title(prestige_level: int) -> str | None:
    """Vrátí exkluzivní titul pro daný prestige level (nebo None)."""
    if prestige_level <= 0:
        return None
    # Najdi nejvyšší prah ≤ prestige_level
    applicable = [lvl for lvl in PRESTIGE_TITLES if lvl <= prestige_level]
    if not applicable:
        return None
    return PRESTIGE_TITLES[max(applicable)]


def prestige_bonus_mult(prestige_level: int) -> dict[str, float]:
    """Vrátí multiplikátory ze všech prestige levelů (kumulativní).

    Bonusy se zvyšují jen do PRESTIGE_POWER_CAP — nad tím jsou čistě kosmetické
    odměny (tituly, portrait frames) bez power escalace.
    """
    pl = max(0, min(prestige_level, PRESTIGE_POWER_CAP))
    return {
        "atk": 1.0 + pl * PRESTIGE_BONUS_ATK_PER_LVL,
        "def": 1.0 + pl * PRESTIGE_BONUS_DEF_PER_LVL,
        "hp":  1.0 + pl * PRESTIGE_BONUS_HP_PER_LVL,
        "mp":  1.0 + pl * PRESTIGE_BONUS_MP_PER_LVL,
    }


def prestige_frame_key(prestige_level: int) -> str | None:
    """Vrátí CSS klíč portrait frame pro daný prestige level (cap na 10)."""
    if prestige_level <= 0:
        return None
    effective = min(prestige_level, PRESTIGE_POWER_CAP)
    return PRESTIGE_FRAME_REWARDS.get(effective)


# ── Prestige log ──────────────────────────────────────────────────────────────
class PrestigeLog(Base):
    __tablename__ = "prestige_log"

    id:              Mapped[int]      = mapped_column(primary_key=True)
    character_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    prestige_level:  Mapped[int]      = mapped_column(Integer, nullable=False)  # nový prestige level
    prestiged_at:    Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reward_crystals: Mapped[int]      = mapped_column(Integer, default=0)
    awarded_title:   Mapped[str | None] = mapped_column(String(64), nullable=True)
