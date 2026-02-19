"""
models/quest.py — Questy a dungeony (time-based auto-fight)
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class QuestStatus(str, enum.Enum):
    IDLE       = "idle"        # Hráč nic nehraje
    ACTIVE     = "active"      # Quest běží
    COLLECTING = "collecting"  # Hotovo, čeká na sebrání odměny

class QuestDifficulty(str, enum.Enum):
    EASY   = "easy"
    NORMAL = "normal"
    HARD   = "hard"
    BOSS   = "boss"

# ── Definice questů ───────────────────────────────────────────────────────────
QUEST_DEFINITIONS = [
    # id, name, desc, difficulty, duration_min, xp, gold_min, gold_max, min_level, icon
    (1,  "Skřeti v lese",        "Vyčisti skupinu skřetů.",              "easy",   2,  25,  15,  30,  1, "🌲"),
    (2,  "Starý hřbitov",        "Prozkoumej opuštěný hřbitov.",         "easy",   3,  35,  20,  40,  1, "🪦"),
    (3,  "Kobky pod hradem",     "Prohledej temné kobky.",               "normal", 5,  60,  40,  70,  2, "🏰"),
    (4,  "Ohnivá jeskyně",       "Přežij žár ohnivé jeskyně.",           "normal", 7,  85,  55, 100,  3, "🔥"),
    (5,  "Temný les",            "Prober se přes les plný netopýrů.",    "normal", 6,  75,  50,  90,  3, "🦇"),
    (6,  "Ruiny dávné civilizace","Prozkumej záhadné ruiny.",            "hard",  10, 140,  90, 150,  5, "🗿"),
    (7,  "Hradní bašta",         "Proraž se přes hradní stráže.",        "hard",  12, 170, 110, 180,  6, "⚔️"),
    (8,  "Dračí hnízdo",         "Loupež v dračím hnízdě.",              "hard",  15, 210, 140, 220,  8, "🐲"),
    (9,  "Věž čaroděje",         "Výstup na vrchol magické věže.",       "hard",  14, 195, 130, 205,  7, "🗼"),
    (10, "BOSS: Kostěný král",   "Epický souboj s Kostěným králem.",     "boss",  20, 400, 300, 500, 10, "💀"),
    (11, "BOSS: Chaos drak",     "Legendární souboj s Chaos Drakem.",    "boss",  30, 700, 600, 900, 15, "🐉"),
    # ── Nové questy ──
    (12, "Bažiny prokletých",    "Proboj se jedovatými bažinami.",       "normal", 6,  80,  55, 95,  4, "🐸"),
    (13, "Pirátský přístav",     "Vyčisti přístav plný pirátů.",         "normal", 8, 105,  70,115,  5, "🏴‍☠️"),
    (14, "Podzemní labyrint",    "Najdi cestu z nekonečného bludišťě.",  "hard",  13, 175, 115,185,  7, "🌀"),
    (15, "Sněžné vrcholky",      "Přežij mráz a horské bestie.",         "hard",  14, 190, 125,195,  8, "🏔️"),
    (16, "Katakomby zla",        "Prohledej katakomby plné nemrtvých.",  "hard",  16, 220, 145,225,  9, "⚰️"),
    (17, "Podvodní chrám",       "Potop se do zatopených ruin chrámu.",  "hard",  18, 250, 160,250, 10, "🌊"),
    (18, "Pustina démonů",       "Přežij démonické pustiny.",            "hard",  20, 290, 190,290, 12, "👿"),
    (19, "Plující ostrov",       "Bojuj na palubě plujícího ostrova.",   "hard",  22, 330, 220,340, 13, "🏝️"),
    (20, "BOSS: Stínový král",   "Střetnutí s pánem temnoty.",           "boss",  35, 900, 700,1100,18, "👤"),
    (21, "BOSS: Věčný drak",     "Drak starý jako samotný svět.",        "boss",  45,1400,1100,1600,25, "🌋"),
]

class Quest(Base):
    __tablename__ = "quests"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), unique=True)

    # Aktuální quest
    quest_def_id:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    status:        Mapped[str]        = mapped_column(String(16), default=QuestStatus.IDLE)
    started_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finish_at:     Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Předpočítaná odměna (vygenerovaná při startu)
    reward_xp:    Mapped[int] = mapped_column(Integer, default=0)
    reward_gold:  Mapped[int] = mapped_column(Integer, default=0)
    reward_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)

    # Výsledek boje
    success:      Mapped[bool] = mapped_column(Boolean, default=True)
    battle_log:   Mapped[str]  = mapped_column(Text, default="")  # JSON string

    character   = relationship("Character", back_populates="quest")
    reward_item = relationship("Item")

    def _finish_at_aware(self):
        """Vrátí finish_at vždy jako timezone-aware datetime (SQLite ukládá naive)."""
        if self.finish_at is None:
            return None
        if self.finish_at.tzinfo is None:
            return self.finish_at.replace(tzinfo=timezone.utc)
        return self.finish_at

    @property
    def is_finished(self) -> bool:
        if self.finish_at is None:
            return False
        # Porovnávej vždy naive UTC (SQLite ignoruje timezone info)
        fa = self.finish_at.replace(tzinfo=None) if self.finish_at.tzinfo else self.finish_at
        return datetime.utcnow() >= fa

    @property
    def seconds_remaining(self) -> int:
        if self.status != QuestStatus.ACTIVE or self.finish_at is None:
            return 0
        fa = self.finish_at.replace(tzinfo=None) if self.finish_at.tzinfo else self.finish_at
        remaining = (fa - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))

    def to_dict(self) -> dict:
        defn = next((q for q in QUEST_DEFINITIONS if q[0] == self.quest_def_id), None)
        return {
            "status": self.status,
            "quest": {
                "id":         defn[0],
                "name":       defn[1],
                "desc":       defn[2],
                "difficulty": defn[3],
                "duration":   defn[4],
                "icon":       defn[9] if len(defn) > 9 else "⚔️",
            } if defn else None,
            "started_at":       self.started_at.isoformat() if self.started_at else None,
            "finish_at":        self.finish_at.isoformat() if self.finish_at else None,
            "seconds_remaining": self.seconds_remaining,
            "is_finished":      self.is_finished,
            "reward_xp":        self.reward_xp,
            "reward_gold":      self.reward_gold,
            "reward_item":      self.reward_item.to_dict() if self.reward_item else None,
            "success":          self.success,
        }
