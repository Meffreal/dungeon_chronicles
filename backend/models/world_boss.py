"""
models/world_boss.py — World Boss model a definice bossů.

World Boss je sdílený PvE cíl pro všechny hráče:
- Obrovský HP pool (škáluje s počtem hráčů)
- Hráči přispívají damage každých 6 hodin
- Fáze bosse se mění globálně
- Odměny po zabitení podle příspěvku hráče
"""
import json
from datetime import datetime, timezone, date as date_type
from sqlalchemy import String, Integer, Float, ForeignKey, Text, DateTime, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

from game.combat_engine import BossPhase


# ── Definice World Bossů ───────────────────────────────────────────────────────
WORLD_BOSS_DEFINITIONS = {
    "skeleton_king": {
        "id":           "skeleton_king",
        "name":         "Kostěný Král",
        "emoji":        "💀",
        "description":  "Starodávný lichový král povstalý z mrtvých. Jeho kosti jsou srostlé s prokletým stříbrem.",
        "min_level":    5,
        "hp_base":      5000,
        "hp_per_player": 800,   # HP se zvyšuje s počtem aktivních hráčů
        "atk":          22,
        "def_":         12,
        "spd":          6,
        "luck":         8,
        "level":        10,
        "respawn_hours": 24,
        "attack_cooldown_hours": 6,
        "phases": [
            BossPhase(
                phase_num=1, trigger_hp_pct=0.70,
                message="Kostěný Král vstává z trůnu! Prokletá energie ho obklopuje!",
                stat_multipliers={},
            ),
            BossPhase(
                phase_num=2, trigger_hp_pct=0.40,
                message="KOSTĚNÝ KRÁL ZUŘÍ! Kosti se tříští a létají vzduchem!",
                stat_multipliers={"atk": 1.4, "spd": 1.25},
                apply_status_to_player="bleed",
            ),
            BossPhase(
                phase_num=3, trigger_hp_pct=0.15,
                message="SMRTONOSNÁ FÁZE! Král volá duchy minulých válečníků!",
                stat_multipliers={"atk": 1.8, "def": 1.3},
                apply_status_to_player="stun",
                heal_pct=0.10,
            ),
        ],
        "special_abilities": ["bone_shatter"],
        "loot_table": {
            "xp_base":      1200,
            "gold_base":    800,
            "bonus_gold_contribution_pct": 0.002,   # 0.2% bonus gold per % damage dealt
        },
    },
    "chaos_dragon": {
        "id":           "chaos_dragon",
        "name":         "Chaos Drak",
        "emoji":        "🐉",
        "description":  "Legendární drak z jiné dimenze. Jeho dech ničí realitu.",
        "min_level":    15,
        "hp_base":      12000,
        "hp_per_player": 1500,
        "atk":          45,
        "def_":         25,
        "spd":          14,
        "luck":         15,
        "level":        20,
        "respawn_hours": 48,
        "attack_cooldown_hours": 6,
        "phases": [
            BossPhase(
                phase_num=1, trigger_hp_pct=0.75,
                message="Chaos Drak rozvinul křídla! Temnota pokrývá bojiště!",
                stat_multipliers={},
            ),
            BossPhase(
                phase_num=2, trigger_hp_pct=0.50,
                message="DRAKŮV HNĚV! Chaos Drak chrlí plamen dimenzí!",
                stat_multipliers={"atk": 1.5},
                apply_status_to_player="burn",
            ),
            BossPhase(
                phase_num=3, trigger_hp_pct=0.25,
                message="KRITICKÁ FÁZE! Chaos Drak se rozpadá do multivesmíru!",
                stat_multipliers={"atk": 2.0, "spd": 1.5},
                apply_status_to_player="weaken",
                heal_pct=0.15,
            ),
        ],
        "special_abilities": ["fire_breath", "chaos_bolt"],
        "loot_table": {
            "xp_base":      3500,
            "gold_base":    2500,
            "bonus_gold_contribution_pct": 0.003,
        },
    },
    "eternal_dragon": {
        "id":           "eternal_dragon",
        "name":         "Věčný Drak",
        "emoji":        "🌋",
        "description":  "Drak starý jako samotný svět. Pouhý jeho pohled paralyzuje.",
        "min_level":    25,
        "hp_base":      25000,
        "hp_per_player": 3000,
        "atk":          80,
        "def_":         45,
        "spd":          20,
        "luck":         20,
        "level":        30,
        "respawn_hours": 72,
        "attack_cooldown_hours": 6,
        "phases": [
            BossPhase(
                phase_num=1, trigger_hp_pct=0.80,
                message="Věčný Drak otevřel oči! Svět se třese jeho přítomností!",
                stat_multipliers={},
            ),
            BossPhase(
                phase_num=2, trigger_hp_pct=0.55,
                message="PROBUZENÍ VĚČNOSTI! Věčný Drak kanalizuje energii stvoření!",
                stat_multipliers={"atk": 1.4, "def": 1.3},
                apply_status_to_player="slow",
            ),
            BossPhase(
                phase_num=3, trigger_hp_pct=0.30,
                message="APOKALYPTICKÁ FÁZE! Věčný Drak otevírá průrvu do nicoty!",
                stat_multipliers={"atk": 1.7},
                apply_status_to_player="weaken",
            ),
            BossPhase(
                phase_num=4, trigger_hp_pct=0.10,
                message="POSLEDNÍ DECH VĚČNOSTI! Drak koncentruje všechnu svou sílu!",
                stat_multipliers={"atk": 2.5, "spd": 1.8},
                apply_status_to_player="stun",
                heal_pct=0.20,
            ),
        ],
        "special_abilities": ["fire_breath", "soul_drain", "chaos_bolt"],
        "loot_table": {
            "xp_base":      7000,
            "gold_base":    5000,
            "bonus_gold_contribution_pct": 0.005,
        },
    },
}


# ── SQLAlchemy modely ──────────────────────────────────────────────────────────

class WorldBoss(Base):
    """Aktivní instance World Bosse (jeden najednou)."""
    __tablename__ = "world_bosses"

    id:           Mapped[int]          = mapped_column(primary_key=True)
    boss_key:     Mapped[str]          = mapped_column(String(32))           # klíč do WORLD_BOSS_DEFINITIONS
    name:         Mapped[str]          = mapped_column(String(64))
    emoji:        Mapped[str]          = mapped_column(String(8), default="💀")

    hp_current:   Mapped[int]          = mapped_column(Integer)
    hp_max:       Mapped[int]          = mapped_column(Integer)
    current_phase: Mapped[int]         = mapped_column(Integer, default=0)

    is_alive:     Mapped[bool]         = mapped_column(Boolean, default=True)
    spawned_at:   Mapped[datetime]     = mapped_column(DateTime)
    killed_at:    Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Serialized phases triggered
    phases_triggered_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    participations = relationship("BossParticipation", back_populates="boss",
                                   cascade="all, delete-orphan")

    def get_phases_triggered(self) -> list[int]:
        if not self.phases_triggered_json:
            return []
        try:
            return json.loads(self.phases_triggered_json)
        except Exception:
            return []

    def add_phase_triggered(self, phase_num: int):
        pts = self.get_phases_triggered()
        if phase_num not in pts:
            pts.append(phase_num)
            self.phases_triggered_json = json.dumps(pts)

    def hp_pct(self) -> float:
        return self.hp_current / max(1, self.hp_max)

    def to_dict(self) -> dict:
        bdef = WORLD_BOSS_DEFINITIONS.get(self.boss_key, {})
        return {
            "id":             self.id,
            "boss_key":       self.boss_key,
            "name":           self.name,
            "emoji":          self.emoji,
            "description":    bdef.get("description", ""),
            "hp_current":     self.hp_current,
            "hp_max":         self.hp_max,
            "hp_pct":         round(self.hp_pct() * 100, 1),
            "current_phase":  self.current_phase,
            "phases_total":   len(bdef.get("phases", [])),
            "is_alive":       self.is_alive,
            "spawned_at":     self.spawned_at.isoformat() if self.spawned_at else None,
            "killed_at":      self.killed_at.isoformat() if self.killed_at else None,
            "min_level":      bdef.get("min_level", 1),
            "attack_cooldown_hours": bdef.get("attack_cooldown_hours", 6),
        }


class BossParticipation(Base):
    """Příspěvek hráče k zabití world bosse."""
    __tablename__ = "boss_participations"

    id:               Mapped[int]      = mapped_column(primary_key=True)
    boss_id:          Mapped[int]      = mapped_column(Integer, ForeignKey("world_bosses.id"))
    character_id:     Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))

    total_damage:     Mapped[int]      = mapped_column(Integer, default=0)
    attacks_count:    Mapped[int]      = mapped_column(Integer, default=0)
    last_attack_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    reward_claimed:   Mapped[bool]     = mapped_column(Boolean, default=False)
    reward_xp:        Mapped[int]      = mapped_column(Integer, default=0)
    reward_gold:      Mapped[int]      = mapped_column(Integer, default=0)

    # Denní tracking — reset každý den UTC půlnoc
    daily_damage:     Mapped[int]             = mapped_column(Integer, default=0)
    daily_date:       Mapped[date_type | None] = mapped_column(Date, nullable=True)

    boss          = relationship("WorldBoss", back_populates="participations")
    character     = relationship("Character")

    def contribution_pct(self, boss: WorldBoss) -> float:
        """Vrátí % příspěvku hráče k celkovému dmg bosse."""
        total = sum(p.total_damage for p in boss.participations)
        if total == 0:
            return 0.0
        return round(self.total_damage / total * 100, 2)

    def to_dict(self) -> dict:
        return {
            "character_id":   self.character_id,
            "total_damage":   self.total_damage,
            "attacks_count":  self.attacks_count,
            "last_attack_at": self.last_attack_at.isoformat() if self.last_attack_at else None,
            "reward_claimed": self.reward_claimed,
            "reward_xp":      self.reward_xp,
            "reward_gold":    self.reward_gold,
        }
