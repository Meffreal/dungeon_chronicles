"""
models/weekly_quest.py — Individuální Weekly Quest Board

Každý hráč dostane 4 týdenní questy (reset pondělí).
Questy jsou deterministicky generovány z week seedu — stejné pro všechny.
"""
import random
from datetime import datetime, timedelta
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


WEEKLY_BOARD_SIZE = 4

WEEKLY_BOARD_POOL = [
    {
        "key":         "kills_50",
        "goal_type":   "kills",
        "goal_target": 50,
        "reward_xp":   300,
        "reward_gold": 500,
        "label":       "Zabij 50 nepřátel",
        "emoji":       "⚔️",
        "desc":        "Plni questy nebo dungeony — každý vítězný boj se počítá.",
    },
    {
        "key":         "kills_100",
        "goal_type":   "kills",
        "goal_target": 100,
        "reward_xp":   600,
        "reward_gold": 1000,
        "label":       "Zabij 100 nepřátel",
        "emoji":       "⚔️",
        "desc":        "Plni questy nebo dungeony — každý vítězný boj se počítá.",
    },
    {
        "key":         "quests_10",
        "goal_type":   "quests",
        "goal_target": 10,
        "reward_xp":   400,
        "reward_gold": 700,
        "label":       "Dokonči 10 questů",
        "emoji":       "📜",
        "desc":        "Úspěšně odevzdej questy na nástěnce.",
    },
    {
        "key":         "quests_20",
        "goal_type":   "quests",
        "goal_target": 20,
        "reward_xp":   800,
        "reward_gold": 1500,
        "label":       "Dokonči 20 questů",
        "emoji":       "📜",
        "desc":        "Úspěšně odevzdej questy na nástěnce.",
    },
    {
        "key":         "arena_3",
        "goal_type":   "arena",
        "goal_target": 3,
        "reward_xp":   350,
        "reward_gold": 600,
        "label":       "Vyhraj 3 arenové zápasy",
        "emoji":       "🏟️",
        "desc":        "PvP souboje v Aréně — jen výhry se počítají.",
    },
    {
        "key":         "arena_5",
        "goal_type":   "arena",
        "goal_target": 5,
        "reward_xp":   700,
        "reward_gold": 1200,
        "label":       "Vyhraj 5 arenových zápasů",
        "emoji":       "🏟️",
        "desc":        "PvP souboje v Aréně — jen výhry se počítají.",
    },
    {
        "key":         "dungeons_2",
        "goal_type":   "dungeons",
        "goal_target": 2,
        "reward_xp":   500,
        "reward_gold": 800,
        "label":       "Projdi 2 dungeony do konce",
        "emoji":       "🏰",
        "desc":        "Dokonči celý dungeon (všechny stagy).",
    },
    {
        "key":         "dungeons_3",
        "goal_type":   "dungeons",
        "goal_target": 3,
        "reward_xp":   900,
        "reward_gold": 1500,
        "label":       "Projdi 3 dungeony do konce",
        "emoji":       "🏰",
        "desc":        "Dokonči celý dungeon (všechny stagy).",
    },
]


def _week_start_for(dt: datetime) -> datetime:
    """Vrátí pondělí 00:00 UTC pro daný datetime."""
    return (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _get_week_pool(week_start: datetime) -> list[dict]:
    """
    Deterministicky vybere WEEKLY_BOARD_SIZE questů pro daný týden.
    Seed = numerická reprezentace roku+týdne → stejné questy pro všechny hráče.
    """
    seed = int(week_start.strftime("%Y%W"))
    rng  = random.Random(seed)
    return rng.sample(WEEKLY_BOARD_POOL, WEEKLY_BOARD_SIZE)


class WeeklyQuestProgress(Base):
    __tablename__ = "weekly_quest_progress"

    id:           Mapped[int]      = mapped_column(primary_key=True)
    character_id: Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))
    week_start:   Mapped[datetime] = mapped_column(DateTime)
    slot:         Mapped[int]      = mapped_column(Integer)       # 0-3
    goal_type:    Mapped[str]      = mapped_column(String(32))    # kills/quests/arena/dungeons
    goal_target:  Mapped[int]      = mapped_column(Integer)
    progress:     Mapped[int]      = mapped_column(Integer, default=0)
    is_completed: Mapped[bool]     = mapped_column(Boolean, default=False)
    reward_xp:    Mapped[int]      = mapped_column(Integer)
    reward_gold:  Mapped[int]      = mapped_column(Integer)
    claimed:      Mapped[bool]     = mapped_column(Boolean, default=False)

    character = relationship("Character")

    def to_dict(self) -> dict:
        pool_entry = next(
            (p for p in WEEKLY_BOARD_POOL
             if p["goal_type"] == self.goal_type and p["goal_target"] == self.goal_target),
            {}
        )
        return {
            "id":           self.id,
            "slot":         self.slot,
            "goal_type":    self.goal_type,
            "goal_target":  self.goal_target,
            "progress":     self.progress,
            "is_completed": self.is_completed,
            "reward_xp":    self.reward_xp,
            "reward_gold":  self.reward_gold,
            "claimed":      self.claimed,
            "can_claim":    self.is_completed and not self.claimed,
            "label":        pool_entry.get("label", self.goal_type),
            "emoji":        pool_entry.get("emoji", "📋"),
            "desc":         pool_entry.get("desc", ""),
            "progress_pct": min(100, round(self.progress / max(1, self.goal_target) * 100)),
        }
