"""
models/world_event.py — World Events systém (komunální sezónní cíle)

Celá komunita hráčů přispívá k společnému cíli (např. "zabijte 10 000 nepřátel").
Po dosažení cíle mohou všichni přispěvatelé vybrat odměnu.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


# ── Typy eventů ───────────────────────────────────────────────────────────────
EVENT_TYPE_LABELS: dict[str, str] = {
    "quests":        "Dokončených questů",
    "kills":         "Zabitých nepřátel",
    "dungeon_clears": "Dokončených dungeonů",
    "boss_damage":   "Poškození World Bosse",
}

# ── Definice aktivních eventů (seed data) ────────────────────────────────────
# Každý event trvá 7 dní od vytvoření, pak může admin/seed vytvořit nový.
WORLD_EVENT_DEFINITIONS: list[dict] = [
    {
        "name": "Týden krve",
        "description": "Komunita dobrodruhů se musí probojovat skrz hordy nepřátel. "
                       "Každý dokončený quest přispívá k celkovému počtu.",
        "event_type": "quests",
        "goal": 500,
        "reward_gold": 1000,
        "reward_crystals": 50,
        "reward_title": "Veterán questů",
        "duration_days": 7,
    },
    {
        "name": "Noční hony",
        "description": "Dungeony volají. Průzkumníci celého Ashenveil musí společně "
                       "projít temná podzemí a přinést světlu vítězství.",
        "event_type": "dungeon_clears",
        "goal": 100,
        "reward_gold": 1500,
        "reward_crystals": 75,
        "reward_title": "Průzkumník hlubin",
        "duration_days": 7,
    },
    {
        "name": "Rána osudu",
        "description": "World Boss hrozí Ashenveil zkázou. Způsobte mu celkem ohromující "
                       "poškození a zachraňte město!",
        "event_type": "boss_damage",
        "goal": 50_000,
        "reward_gold": 2000,
        "reward_crystals": 100,
        "reward_title": "Zabijec bohů",
        "duration_days": 7,
    },
]


# ── Modely ─────────────────────────────────────────────────────────────────────
class WorldEvent(Base):
    __tablename__ = "world_events"

    id:              Mapped[int]      = mapped_column(primary_key=True)
    name:            Mapped[str]      = mapped_column(String(128), nullable=False)
    description:     Mapped[str]      = mapped_column(Text, nullable=True)
    event_type:      Mapped[str]      = mapped_column(String(32), nullable=False)   # viz EVENT_TYPE_LABELS
    goal:            Mapped[int]      = mapped_column(Integer, nullable=False)
    current_progress:Mapped[int]      = mapped_column(Integer, default=0)
    starts_at:       Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at:         Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active:       Mapped[bool]     = mapped_column(Boolean, default=True)
    is_completed:    Mapped[bool]     = mapped_column(Boolean, default=False)
    reward_gold:     Mapped[int]      = mapped_column(Integer, default=0)
    reward_crystals: Mapped[int]      = mapped_column(Integer, default=0)
    reward_title:    Mapped[str|None] = mapped_column(String(64), nullable=True)

    def to_dict(self) -> dict:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        remaining_secs = max(0, int((self.ends_at - now).total_seconds())) if self.ends_at > now else 0
        pct = min(100, round(self.current_progress / self.goal * 100, 1)) if self.goal > 0 else 0
        return {
            "id":               self.id,
            "name":             self.name,
            "description":      self.description,
            "event_type":       self.event_type,
            "event_type_label": EVENT_TYPE_LABELS.get(self.event_type, self.event_type),
            "goal":             self.goal,
            "current_progress": self.current_progress,
            "progress_pct":     pct,
            "starts_at":        self.starts_at.isoformat(),
            "ends_at":          self.ends_at.isoformat(),
            "remaining_seconds": remaining_secs,
            "is_active":        self.is_active,
            "is_completed":     self.is_completed,
            "reward_gold":      self.reward_gold,
            "reward_crystals":  self.reward_crystals,
            "reward_title":     self.reward_title,
        }


class WorldEventContrib(Base):
    """Příspěvek jednoho hráče k eventu (kumulativní)."""
    __tablename__ = "world_event_contribs"

    id:             Mapped[int]      = mapped_column(primary_key=True)
    event_id:       Mapped[int]      = mapped_column(Integer, ForeignKey("world_events.id"), nullable=False)
    character_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    contribution:   Mapped[int]      = mapped_column(Integer, default=0)
    last_contrib_at:Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WorldEventClaim(Base):
    """Záznam o vybrání odměny za event."""
    __tablename__ = "world_event_claims"

    id:               Mapped[int]      = mapped_column(primary_key=True)
    event_id:         Mapped[int]      = mapped_column(Integer, ForeignKey("world_events.id"), nullable=False)
    character_id:     Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    claimed_at:       Mapped[datetime] = mapped_column(DateTime, nullable=False)
    gold_received:    Mapped[int]      = mapped_column(Integer, default=0)
    crystals_received:Mapped[int]      = mapped_column(Integer, default=0)
