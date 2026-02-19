"""
models/character.py — Postava, stats, inventář, equipment
"""
import json
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base
import enum

class CharacterClass(str, enum.Enum):
    WARRIOR = "warrior"
    MAGE    = "mage"
    RANGER  = "ranger"

# ── Base stats per třída (hodnoty na level 1) ─────────────────────────────────
CLASS_BASE_STATS = {
    CharacterClass.WARRIOR: {
        "strength": 15, "dexterity": 8,  "intelligence": 5,
        "endurance": 12, "luck": 5,
        "hp_base": 120,  "mp_base": 30,
        "atk_base": 18,  "def_base": 14, "spd_base": 8,
        "description": "Silný bojovník v přední linii. Vysoký HP a obrana.",
        "emoji": "⚔️",
    },
    CharacterClass.MAGE: {
        "strength": 5,  "dexterity": 8,  "intelligence": 18,
        "endurance": 6,  "luck": 8,
        "hp_base": 70,   "mp_base": 120,
        "atk_base": 10,  "def_base": 5,  "spd_base": 10,
        "description": "Mistr arkánné magie. Devastující kouzla, křehké tělo.",
        "emoji": "🔮",
    },
    CharacterClass.RANGER: {
        "strength": 9,  "dexterity": 16, "intelligence": 8,
        "endurance": 9,  "luck": 13,
        "hp_base": 90,   "mp_base": 60,
        "atk_base": 14,  "def_base": 8,  "spd_base": 18,
        "description": "Rychlý a přesný lovec. Mistr dálkového boje a pastí.",
        "emoji": "🏹",
    },
}

# ── XP křivka ─────────────────────────────────────────────────────────────────
def xp_for_level(level: int) -> int:
    """Kolik XP celkem je potřeba pro daný level."""
    return int(100 * (level ** 1.8))

def xp_to_next(level: int) -> int:
    """Kolik XP je potřeba pro přechod z `level` na `level+1`."""
    return xp_for_level(level + 1) - xp_for_level(level)

# ── Character model ───────────────────────────────────────────────────────────
class Character(Base):
    __tablename__ = "characters"

    id:         Mapped[int] = mapped_column(primary_key=True)
    user_id:    Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name:       Mapped[str] = mapped_column(String(32), unique=True, index=True)
    cls:        Mapped[str] = mapped_column(String(16))   # CharacterClass value
    level:      Mapped[int] = mapped_column(Integer, default=1)
    xp:         Mapped[int] = mapped_column(Integer, default=0)
    gold:       Mapped[int] = mapped_column(Integer, default=150)

    # Primary stats
    strength:     Mapped[int] = mapped_column(Integer, default=5)
    dexterity:    Mapped[int] = mapped_column(Integer, default=5)
    intelligence: Mapped[int] = mapped_column(Integer, default=5)
    endurance:    Mapped[int] = mapped_column(Integer, default=5)
    luck:         Mapped[int] = mapped_column(Integer, default=5)

    # Derived / combat stats (přepočítávají se při equipu)
    hp_max:  Mapped[int] = mapped_column(Integer, default=100)
    mp_max:  Mapped[int] = mapped_column(Integer, default=50)
    atk:     Mapped[int] = mapped_column(Integer, default=10)
    def_:    Mapped[int] = mapped_column(Integer, default=5)
    spd:     Mapped[int] = mapped_column(Integer, default=8)

    # Equip sloty (item ID nebo null)
    eq_weapon:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_helmet:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_armor:   Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_gloves:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_boots:   Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_ring:    Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    eq_amulet:  Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)

    # Arena
    arena_rank:          Mapped[int]            = mapped_column(Integer, default=1000)  # ELO-like
    arena_wins:          Mapped[int]            = mapped_column(Integer, default=0)
    arena_losses:        Mapped[int]            = mapped_column(Integer, default=0)
    arena_cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Guild
    guild_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("guilds.id"), nullable=True)

    # Statistiky pro achievementy
    quests_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Nerozdělelné stat body (získávají se za každý level up)
    stat_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Vztahy
    user      = relationship("User", back_populates="character")
    inventory = relationship("InventoryItem", back_populates="character")
    quest          = relationship("Quest", back_populates="character", uselist=False)
    notifications  = relationship("Notification", back_populates="character", cascade="all, delete-orphan")
    guild     = relationship("Guild", back_populates="members", foreign_keys=[guild_id])

    def recalculate_stats(self):
        """Přepočítá combat stats z primary stats + level bonusů."""
        lvl = self.level
        self.hp_max  = self.hp_base  + self.endurance * 8  + lvl * 5
        self.mp_max  = self.mp_base  + self.intelligence * 4 + lvl * 2
        self.atk     = self.atk_base + self.strength * 2   + self.dexterity + lvl * 2
        self.def_    = self.def_base + self.endurance * 2  + lvl
        self.spd     = self.spd_base + self.dexterity * 2  + self.luck // 2

    @property
    def hp_base(self) -> int:
        return CLASS_BASE_STATS[CharacterClass(self.cls)]["hp_base"]

    @property
    def mp_base(self) -> int:
        return CLASS_BASE_STATS[CharacterClass(self.cls)]["mp_base"]

    @property
    def atk_base(self) -> int:
        return CLASS_BASE_STATS[CharacterClass(self.cls)]["atk_base"]

    @property
    def def_base(self) -> int:
        return CLASS_BASE_STATS[CharacterClass(self.cls)]["def_base"]

    @property
    def spd_base(self) -> int:
        return CLASS_BASE_STATS[CharacterClass(self.cls)]["spd_base"]

    @property
    def xp_to_next_level(self) -> int:
        return xp_to_next(self.level)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cls": self.cls,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next_level,
            "gold": self.gold,
            "stats": {
                "strength": self.strength,
                "dexterity": self.dexterity,
                "intelligence": self.intelligence,
                "endurance": self.endurance,
                "luck": self.luck,
            },
            "combat": {
                "hp_max": self.hp_max,
                "mp_max": self.mp_max,
                "atk": self.atk,
                "def": self.def_,
                "spd": self.spd,
            },
            "stat_points": self.stat_points or 0,
            "arena": {
                "rank": self.arena_rank,
                "wins": self.arena_wins,
                "losses": self.arena_losses,
                "cooldown_until": self.arena_cooldown_until.isoformat() if self.arena_cooldown_until else None,
            },
            "equipment": {
                "weapon":  self.eq_weapon,
                "helmet":  self.eq_helmet,
                "armor":   self.eq_armor,
                "gloves":  self.eq_gloves,
                "boots":   self.eq_boots,
                "ring":    self.eq_ring,
                "amulet":  self.eq_amulet,
            },
        }
