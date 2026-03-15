"""
models/guild_war.py — Guild Wars (asynchronní formát)

Každý cech může vyhlásit válku jinému cechu.
Válka trvá 24 hodin, každý člen může zaútočit 3× na soupeřovy členy.
Vítěz (více bodů) získá guild XP odměnu.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────
WAR_DURATION_HOURS    = 24      # délka války v hodinách
MAX_ATTACKS_PER_WAR   = 3       # počet útoků na člena za celou válku
POINTS_WIN            = 3       # body za výhru útoku
POINTS_LOSS           = 1       # body i za prohru (participation)
REWARD_XP_WIN         = 500     # guild XP pro vítěze
REWARD_XP_LOSS        = 100     # guild XP pro poraženého


class GuildWar(Base):
    __tablename__ = "guild_wars"

    id:                 Mapped[int]       = mapped_column(primary_key=True)
    attacker_guild_id:  Mapped[int]       = mapped_column(Integer, ForeignKey("guilds.id"), nullable=False)
    defender_guild_id:  Mapped[int]       = mapped_column(Integer, ForeignKey("guilds.id"), nullable=False)
    started_at:         Mapped[datetime]  = mapped_column(DateTime, nullable=False)
    ends_at:            Mapped[datetime]  = mapped_column(DateTime, nullable=False)
    status:             Mapped[str]       = mapped_column(String(16), default="active")  # active|completed
    winner_guild_id:    Mapped[int | None] = mapped_column(Integer, ForeignKey("guilds.id"), nullable=True)  # null = remíza
    attacker_points:    Mapped[int]       = mapped_column(Integer, default=0)
    defender_points:    Mapped[int]       = mapped_column(Integer, default=0)

    def to_dict(self) -> dict:
        return {
            "id":                self.id,
            "attacker_guild_id": self.attacker_guild_id,
            "defender_guild_id": self.defender_guild_id,
            "started_at":        self.started_at.isoformat(),
            "ends_at":           self.ends_at.isoformat(),
            "status":            self.status,
            "winner_guild_id":   self.winner_guild_id,
            "attacker_points":   self.attacker_points,
            "defender_points":   self.defender_points,
        }


class GuildWarAttack(Base):
    __tablename__ = "guild_war_attacks"

    id:               Mapped[int]      = mapped_column(primary_key=True)
    war_id:           Mapped[int]      = mapped_column(Integer, ForeignKey("guild_wars.id"), nullable=False)
    attacker_char_id: Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    defender_char_id: Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    attacker_won:     Mapped[bool]     = mapped_column(Boolean, nullable=False)
    points_earned:    Mapped[int]      = mapped_column(Integer, default=0)
    attacked_at:      Mapped[datetime] = mapped_column(DateTime, nullable=False)
    events_json:      Mapped[str | None] = mapped_column(Text, nullable=True)  # zkrácený combat log
