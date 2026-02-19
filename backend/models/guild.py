"""
models/guild.py — Cechy + Guild Dungeon
"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Dungeon bossi ──────────────────────────────────────────────────────────────
GUILD_BOSSES = [
    {"name": "Goblinský král",    "emoji": "👺", "hp_base": 3000,  "xp_reward": 150,  "gold_reward": 250},
    {"name": "Kamenný golem",     "emoji": "🗿", "hp_base": 6000,  "xp_reward": 280,  "gold_reward": 450},
    {"name": "Temný nekromancer", "emoji": "💀", "hp_base": 10000, "xp_reward": 450,  "gold_reward": 750},
    {"name": "Ohnivý drak",       "emoji": "🐉", "hp_base": 16000, "xp_reward": 700,  "gold_reward": 1200},
    {"name": "Stínový démon",     "emoji": "👾", "hp_base": 24000, "xp_reward": 1000, "gold_reward": 1800},
]

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
        return {
            "id":           self.id,
            "name":         self.name,
            "description":  self.description,
            "level":        self.level,
            "xp":           self.xp,
            "gold":         self.gold,
            "emblem":       self.emblem,
            "member_count": member_count,
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
