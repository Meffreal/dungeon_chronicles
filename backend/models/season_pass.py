"""
models/season_pass.py — Sezónní progression (free track)

SeasonPass  = definice jedné sezóny (název, trvání, je aktivní)
SeasonPassProgress = progress hráče v dané sezóně
"""
import json
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


SEASON_PASS_DURATION_DAYS = 42   # 6 týdnů
MAX_TIER = 10

# ── XP za aktivity ────────────────────────────────────────────────────────────
SEASON_XP_SOURCES = {
    "quest":            10,   # úspěšný collect questu
    "arena_win":        15,   # vítězství v aréně
    "dungeon_stage":     5,   # každý stage v dungeonu
    "dungeon_complete":  20,  # bonus za dokončení celého dungeonu
    "weekly_claim":      30,  # claim weekly board questu
}

# ── Reward track ──────────────────────────────────────────────────────────────
# reward_type: "title" | "gold" | "title_and_gold"
SEASON_TIERS = [
    {
        "tier": 1,  "xp_req": 100,
        "reward_type": "title",         "reward_title": "Dobrodruh sezóny",  "reward_gold": 0,    "reward_crystals": 0,
        "emoji": "⚜",  "label": "Titul: Dobrodruh sezóny",
    },
    {
        "tier": 2,  "xp_req": 250,
        "reward_type": "gold",          "reward_title": None,                "reward_gold": 300,  "reward_crystals": 30,
        "emoji": "💰", "label": "+300 G · +30 💎",
    },
    {
        "tier": 3,  "xp_req": 450,
        "reward_type": "title",         "reward_title": "Veterán sezóny",   "reward_gold": 0,    "reward_crystals": 0,
        "emoji": "⚔️",  "label": "Titul: Veterán sezóny",
    },
    {
        "tier": 4,  "xp_req": 700,
        "reward_type": "gold",          "reward_title": None,                "reward_gold": 600,  "reward_crystals": 50,
        "emoji": "💰", "label": "+600 G · +50 💎",
    },
    {
        "tier": 5,  "xp_req": 1000,
        "reward_type": "title",         "reward_title": "Šampion sezóny",   "reward_gold": 0,    "reward_crystals": 0,
        "emoji": "🏆", "label": "Titul: Šampion sezóny",
    },
    {
        "tier": 6,  "xp_req": 1400,
        "reward_type": "gold",          "reward_title": None,                "reward_gold": 1000, "reward_crystals": 75,
        "emoji": "💰", "label": "+1 000 G · +75 💎",
    },
    {
        "tier": 7,  "xp_req": 1900,
        "reward_type": "title",         "reward_title": "Rytíř sezóny",     "reward_gold": 0,    "reward_crystals": 0,
        "emoji": "⚔️",  "label": "Titul: Rytíř sezóny",
    },
    {
        "tier": 8,  "xp_req": 2500,
        "reward_type": "gold",          "reward_title": None,                "reward_gold": 1500, "reward_crystals": 100,
        "emoji": "💰", "label": "+1 500 G · +100 💎",
    },
    {
        "tier": 9,  "xp_req": 3200,
        "reward_type": "title",         "reward_title": "Hrdina sezóny",    "reward_gold": 0,    "reward_crystals": 0,
        "emoji": "🏅", "label": "Titul: Hrdina sezóny",
    },
    {
        "tier": 10, "xp_req": 4000,
        "reward_type": "title_and_gold","reward_title": "Legenda sezóny",   "reward_gold": 3000, "reward_crystals": 150,
        "emoji": "👑", "label": "Titul: Legenda sezóny + 3 000 G · +150 💎",
    },
]


def get_reached_tier(season_xp: int) -> int:
    """Vrátí nejvyšší dosažený tier na základě nasbíraného XP."""
    tier = 0
    for t in SEASON_TIERS:
        if season_xp >= t["xp_req"]:
            tier = t["tier"]
        else:
            break
    return tier


class SeasonPass(Base):
    __tablename__ = "season_passes"

    id:          Mapped[int]      = mapped_column(primary_key=True)
    season_num:  Mapped[int]      = mapped_column(Integer, default=1)
    name:        Mapped[str]      = mapped_column(String(64))
    start_date:  Mapped[datetime] = mapped_column(DateTime)
    end_date:    Mapped[datetime] = mapped_column(DateTime)
    is_active:   Mapped[bool]     = mapped_column(Boolean, default=True)

    progress = relationship("SeasonPassProgress", back_populates="season")

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "season_num": self.season_num,
            "name":       self.name,
            "start_date": self.start_date.isoformat(),
            "end_date":   self.end_date.isoformat(),
            "is_active":  self.is_active,
            "tiers":      SEASON_TIERS,
        }


class SeasonPassProgress(Base):
    __tablename__ = "season_pass_progress"

    id:            Mapped[int]      = mapped_column(primary_key=True)
    character_id:  Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))
    season_id:     Mapped[int]      = mapped_column(Integer, ForeignKey("season_passes.id"))
    season_xp:     Mapped[int]      = mapped_column(Integer, default=0)
    claimed_tiers: Mapped[str]      = mapped_column(Text, default="[]")   # JSON list[int]

    season    = relationship("SeasonPass", back_populates="progress")
    character = relationship("Character")

    def get_claimed(self) -> list[int]:
        try:
            return json.loads(self.claimed_tiers or "[]")
        except Exception:
            return []

    def mark_claimed(self, tier: int) -> None:
        claimed = self.get_claimed()
        if tier not in claimed:
            claimed.append(tier)
            self.claimed_tiers = json.dumps(sorted(claimed))

    def to_dict(self) -> dict:
        claimed   = self.get_claimed()
        reached   = get_reached_tier(self.season_xp)
        next_tier = next((t for t in SEASON_TIERS if t["tier"] > reached), None)
        return {
            "season_xp":     self.season_xp,
            "reached_tier":  reached,
            "claimed_tiers": claimed,
            "next_tier":     next_tier,
            "next_xp_req":   next_tier["xp_req"] if next_tier else None,
            "tiers_status":  [
                {
                    **t,
                    "reached": self.season_xp >= t["xp_req"],
                    "claimed": t["tier"] in claimed,
                    "can_claim": self.season_xp >= t["xp_req"] and t["tier"] not in claimed,
                }
                for t in SEASON_TIERS
            ],
        }
