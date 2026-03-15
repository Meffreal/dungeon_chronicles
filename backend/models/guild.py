"""
models/guild.py — Cechy + Guild Dungeon + Guild Weekly Quest
"""
import random
from datetime import datetime, timedelta
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Dungeon bossi — načteni z config/guild_bosses.json ────────────────────────
# Přidat nového bosse = přidat řádek do backend/config/guild_bosses.json
from game.config_loader import load_guild_bosses as _lgb
GUILD_BOSSES = _lgb()

class Guild(Base):
    __tablename__ = "guilds"

    id:          Mapped[int] = mapped_column(primary_key=True)
    name:        Mapped[str] = mapped_column(String(48), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    leader_id:   Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    level:       Mapped[int] = mapped_column(Integer, default=1)
    xp:          Mapped[int] = mapped_column(Integer, default=0)
    gold:        Mapped[int] = mapped_column(Integer, default=0)  # guild banka
    emblem:      Mapped[str] = mapped_column(String(8), default="🛡️")
    created_at:  Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members = relationship("Character", back_populates="guild", foreign_keys="Character.guild_id")
    leader  = relationship("Character", foreign_keys=[leader_id])

    def to_dict(self, member_count: int = 0) -> dict:
        from game.guild_xp import xp_to_next, get_perks
        perks = get_perks(self.level)
        return {
            "id":           self.id,
            "name":         self.name,
            "description":  self.description,
            "level":        self.level,
            "xp":           self.xp,
            "xp_to_next":   xp_to_next(self.level),
            "rank_name":    perks["name"],
            "rank_emoji":   perks["emoji"],
            "gold":         self.gold,
            "emblem":       self.emblem,
            "member_count": member_count,
            "member_cap":   perks["member_cap"],
            "created_at":   str(self.created_at),
        }


class GuildDungeon(Base):
    __tablename__ = "guild_dungeons"

    id:              Mapped[int]            = mapped_column(primary_key=True)
    guild_id:        Mapped[int]            = mapped_column(Integer, ForeignKey("guilds.id"))
    boss_index:      Mapped[int]            = mapped_column(Integer, default=0)
    boss_name:       Mapped[str]            = mapped_column(String(64))
    boss_emoji:      Mapped[str]            = mapped_column(String(8), default="👹")
    boss_hp_max:     Mapped[int]            = mapped_column(Integer)
    boss_hp_current: Mapped[int]            = mapped_column(Integer)
    is_defeated:     Mapped[bool]           = mapped_column(Boolean, default=False)
    started_at:      Mapped[datetime]       = mapped_column(DateTime, default=datetime.utcnow)
    defeated_at:     Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    contribs = relationship("GuildDungeonContrib", back_populates="dungeon")

    @property
    def hp_percent(self) -> int:
        return round(max(0, self.boss_hp_current) / self.boss_hp_max * 100)

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "boss_name":       f"{self.boss_emoji} {self.boss_name}",
            "boss_emoji":      self.boss_emoji,
            "boss_hp_max":     self.boss_hp_max,
            "boss_hp_current": max(0, self.boss_hp_current),
            "hp_percent":      self.hp_percent,
            "is_defeated":     self.is_defeated,
            "started_at":      self.started_at.isoformat(),
            "defeated_at":     self.defeated_at.isoformat() if self.defeated_at else None,
        }


class GuildDungeonContrib(Base):
    __tablename__ = "guild_dungeon_contribs"

    id:             Mapped[int]            = mapped_column(primary_key=True)
    dungeon_id:     Mapped[int]            = mapped_column(Integer, ForeignKey("guild_dungeons.id"))
    character_id:   Mapped[int]            = mapped_column(Integer, ForeignKey("characters.id"))
    damage_dealt:   Mapped[int]            = mapped_column(Integer, default=0)
    last_attack_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    dungeon   = relationship("GuildDungeon", back_populates="contribs")
    character = relationship("Character")

    def to_dict(self) -> dict:
        return {
            "character_id":   self.character_id,
            "name":           self.character.name if self.character else "?",
            "cls":            self.character.cls  if self.character else "",
            "damage_dealt":   self.damage_dealt,
            "last_attack_at": self.last_attack_at.isoformat() if self.last_attack_at else None,
        }


class GuildMessage(Base):
    __tablename__ = "guild_messages"

    id:           Mapped[int] = mapped_column(primary_key=True)
    guild_id:     Mapped[int] = mapped_column(Integer, ForeignKey("guilds.id"))
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    text:         Mapped[str] = mapped_column(Text)
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    character = relationship("Character")

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "character_id": self.character_id,
            "author":       self.character.name if self.character else "?",
            "author_cls":   self.character.cls if self.character else "",
            "text":         self.text,
            "created_at":   self.created_at.isoformat(),
        }


# ── Guild Weekly Quest ─────────────────────────────────────────────────────────

WEEKLY_QUEST_POOL = [
    {
        "goal_type":   "kills",
        "goal_target": 100,
        "reward_gold": 800,
        "label":       "Zabijte celkem 100 nepřátel",
        "emoji":       "⚔",
        "desc":        "Dokončujte questy a dungeony — každý vítězný boj se počítá.",
    },
    {
        "goal_type":   "quests",
        "goal_target": 30,
        "reward_gold": 1200,
        "label":       "Dokončete celkem 30 questů",
        "emoji":       "📜",
        "desc":        "Plňte questy — každý úspěšně odevzdaný quest se počítá.",
    },
    {
        "goal_type":   "dungeons",
        "goal_target": 5,
        "reward_gold": 2000,
        "label":       "Projděte 5 dungeonů do konce",
        "emoji":       "🏰",
        "desc":        "Projděte celý dungeon (všechny stagy) — každé dokončení se počítá.",
    },
]


def _week_start_for(dt: datetime) -> datetime:
    """Vrátí datum pondělí (00:00) pro daný datetime (UTC)."""
    return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


class GuildWeeklyQuest(Base):
    __tablename__ = "guild_weekly_quests"

    id:           Mapped[int]           = mapped_column(primary_key=True)
    guild_id:     Mapped[int]           = mapped_column(Integer, ForeignKey("guilds.id"))
    week_start:   Mapped[datetime]      = mapped_column(DateTime)
    goal_type:    Mapped[str]           = mapped_column(String(32))   # kills / quests / dungeons
    goal_target:  Mapped[int]           = mapped_column(Integer)
    progress:     Mapped[int]           = mapped_column(Integer, default=0)
    is_completed: Mapped[bool]          = mapped_column(Boolean, default=False)
    reward_gold:  Mapped[int]           = mapped_column(Integer)
    completed_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    contribs = relationship("GuildWeeklyContrib", back_populates="weekly_quest")

    def to_dict(self) -> dict:
        pool_entry = next((p for p in WEEKLY_QUEST_POOL if p["goal_type"] == self.goal_type), {})
        return {
            "id":           self.id,
            "guild_id":     self.guild_id,
            "week_start":   self.week_start.isoformat(),
            "goal_type":    self.goal_type,
            "goal_target":  self.goal_target,
            "progress":     self.progress,
            "is_completed": self.is_completed,
            "reward_gold":  self.reward_gold,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "label":        pool_entry.get("label", self.goal_type),
            "emoji":        pool_entry.get("emoji", "📋"),
            "desc":         pool_entry.get("desc", ""),
            "progress_pct": min(100, round(self.progress / max(1, self.goal_target) * 100)),
        }


class GuildWeeklyContrib(Base):
    __tablename__ = "guild_weekly_contribs"

    id:           Mapped[int] = mapped_column(primary_key=True)
    quest_id:     Mapped[int] = mapped_column(Integer, ForeignKey("guild_weekly_quests.id"))
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))
    contribution: Mapped[int] = mapped_column(Integer, default=0)

    weekly_quest = relationship("GuildWeeklyQuest", back_populates="contribs")
    character    = relationship("Character")

    def to_dict(self) -> dict:
        return {
            "character_id": self.character_id,
            "name":         self.character.name if self.character else "?",
            "cls":          self.character.cls  if self.character else "",
            "contribution": self.contribution,
        }
