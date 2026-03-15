"""
models/agent.py — Stínový Agent: operace, identity a counter-intelligence
"""
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────

IDENTITY_REVEAL_HOURS = 72     # jak dlouho trvá odhalení identity
COVER_XP_MILESTONE_DAYS = [7, 30]  # ve dnech – milníky pro XP za udržení krytu

# Délka operací podle obtížnosti (minuty)
OPERATION_DURATIONS = {
    "easy":   {"min": 30,  "max": 60},
    "normal": {"min": 120, "max": 240},
    "hard":   {"min": 360, "max": 720},
}

# Šance na odhalení podle obtížnosti a ranku Agenta (index = rank)
DETECTION_CHANCE = {
    "easy":   [0.30, 0.20, 0.12, 0.06, 0.02, 0.0],
    "normal": [0.60, 0.45, 0.30, 0.18, 0.08, 0.02],
    "hard":   [0.90, 0.70, 0.50, 0.30, 0.15, 0.05],
}

# XP tabulka
AGENT_XP = {
    "operation_success_easy":   120,
    "operation_success_normal": 200,
    "operation_success_hard":   380,
    "operation_detected":        30,   # i detekce dá malé XP
    "intel_confirmed":          100,   # bonus pokud se intel ukázal správný
    "cover_7_days":             150,
    "cover_30_days":            500,
    "counter_intel_success":    250,   # odhalení cizího Agenta
    "phantom_easy":             72,    # 60 % normal sazby
    "phantom_normal":           120,
    "phantom_hard":             228,
}

# Typy operací
OPERATION_TYPES = [
    "reconnaissance",   # průzkum cechu/hráče – vrátí intel o dungeon aktivitě, online časy
    "infiltration",     # přístup k tržním trendům, sell rate historii
    "sabotage",         # zvýší quest fail chance cíle o X % na Y hodin
    "counter_intel",    # odhalení Agentů sledujících tebe nebo jiného hráče
]


# ── Modely ────────────────────────────────────────────────────────────────────

class AgentOperation(Base):
    """
    Jedna operace Agenta. Probíhá časově (started_at → finish_at).
    Po finish_at router/service dovolí collect() – podobně jako quest collect.

    is_phantom = True → cíl je NPC (Phantom Contract), XP je snížené.
    intel_result_json obsahuje výsledek: co Agent zjistil, jaký dopad měla sabotáž apod.
    """
    __tablename__ = "agent_operations"

    id:               Mapped[int] = mapped_column(primary_key=True)
    agent_char_id:    Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))

    operation_type:   Mapped[str] = mapped_column(String(32))    # viz OPERATION_TYPES
    difficulty:       Mapped[str] = mapped_column(String(16), default="normal")   # easy | normal | hard

    # Cíl (alespoň jedno musí být vyplněno, nebo is_phantom = True)
    target_char_id:   Mapped[int | None] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)
    target_guild_id:  Mapped[int | None] = mapped_column(Integer, ForeignKey("guilds.id"), nullable=True)
    is_phantom:       Mapped[bool]       = mapped_column(Boolean, default=False)

    # Časování
    started_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    finish_at:        Mapped[datetime]      = mapped_column(DateTime)
    collected_at:     Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Výsledek
    status:           Mapped[str]       = mapped_column(String(16), default="active")
    # active | completed | detected | failed
    was_detected:     Mapped[bool]      = mapped_column(Boolean, default=False)
    intel_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sabotáž specifika – ukládáme sem co přesně bylo aplikováno na cíl
    sabotage_effect_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    xp_awarded:       Mapped[bool]      = mapped_column(Boolean, default=False)

    agent       = relationship("Character", foreign_keys=[agent_char_id])
    target_char = relationship("Character", foreign_keys=[target_char_id])

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_finished(self) -> bool:
        return datetime.now(timezone.utc).replace(tzinfo=None) >= self.finish_at.replace(tzinfo=None)

    @property
    def seconds_remaining(self) -> int:
        delta = self.finish_at.replace(tzinfo=None) - datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0, int(delta.total_seconds()))

    def get_intel(self) -> dict:
        try:
            return json.loads(self.intel_result_json) if self.intel_result_json else {}
        except Exception:
            return {}

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "operation_type":   self.operation_type,
            "difficulty":       self.difficulty,
            "is_phantom":       self.is_phantom,
            "status":           self.status,
            "was_detected":     self.was_detected,
            "started_at":       self.started_at.isoformat(),
            "finish_at":        self.finish_at.isoformat(),
            "is_finished":      self.is_finished,
            "seconds_remaining": self.seconds_remaining,
            "intel":            self.get_intel() if self.collected_at else None,
        }


class AgentIdentity(Base):
    """
    Každý Agent má pseudonym. Tabulka je 1:1 s Character.
    Záznam vzniká při prvním aktivování Agent profese.

    is_hard_target: hráč se dobrovolně stane "tvrdým cílem" –
    Agenti ho mohou napadnout, ale on dostane odměny za každou detekovanou operaci.
    """
    __tablename__ = "agent_identities"

    character_id:           Mapped[int]  = mapped_column(Integer, ForeignKey("characters.id"), primary_key=True)
    pseudonym:              Mapped[str]  = mapped_column(String(64), unique=True)

    is_revealed:            Mapped[bool]           = mapped_column(Boolean, default=False)
    revealed_until:         Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Sledování krytu pro XP milníky
    cover_maintained_since: Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    cover_7d_xp_awarded:    Mapped[bool]            = mapped_column(Boolean, default=False)
    cover_30d_xp_awarded:   Mapped[bool]            = mapped_column(Boolean, default=False)

    # Opt-in jako tvrdý cíl
    is_hard_target:         Mapped[bool] = mapped_column(Boolean, default=False)

    # Suspicion Meter – kolik operací bylo detekováno (NPC strany nebo ostatních hráčů)
    times_detected:         Mapped[int]  = mapped_column(Integer, default=0, server_default="0")

    character = relationship("Character")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_currently_revealed(self) -> bool:
        if not self.is_revealed:
            return False
        if self.revealed_until is None:
            return True
        return datetime.now(timezone.utc).replace(tzinfo=None) < self.revealed_until.replace(tzinfo=None)

    @property
    def cover_days(self) -> int:
        """Kolik dní trvá aktuální kryt (od posledního resetu)."""
        return (datetime.now(timezone.utc).replace(tzinfo=None) - self.cover_maintained_since.replace(tzinfo=None)).days

    def reveal(self) -> None:
        """Odhalí identitu na IDENTITY_REVEAL_HOURS hodin a resetuje cover timer."""
        self.is_revealed = True
        self.revealed_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=IDENTITY_REVEAL_HOURS)
        self.cover_maintained_since = datetime.now(timezone.utc).replace(tzinfo=None)
        self.cover_7d_xp_awarded = False
        self.cover_30d_xp_awarded = False
        self.times_detected += 1

    def to_dict(self) -> dict:
        return {
            "pseudonym":             self.pseudonym,
            "is_revealed":           self.is_currently_revealed,
            "revealed_until":        self.revealed_until.isoformat() if self.revealed_until else None,
            "cover_days":            self.cover_days,
            "cover_maintained_since": self.cover_maintained_since.isoformat() if self.cover_maintained_since else None,
            "is_hard_target":        self.is_hard_target,
            "times_detected":        self.times_detected,
        }


class SabotageEffect(Base):
    """
    Aktivní sabotáž na cílovém hráči. Zvyšuje jeho quest fail chance.
    Při každém quest collect se zkontroluje existence záznamu a aplikuje penalizace.
    Záznam se smaže po expires_at.
    """
    __tablename__ = "sabotage_effects"

    id:               Mapped[int]      = mapped_column(primary_key=True)
    target_char_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))
    agent_char_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("characters.id"))
    operation_id:     Mapped[int]      = mapped_column(Integer, ForeignKey("agent_operations.id"))

    # Míra sabotáže – snížení quest success rate v procentech
    fail_penalty_pct: Mapped[int]      = mapped_column(Integer, default=10)   # např. 10 = -10 %
    applied_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:       Mapped[datetime] = mapped_column(DateTime)

    target = relationship("Character", foreign_keys=[target_char_id])
    agent  = relationship("Character", foreign_keys=[agent_char_id])

    @property
    def is_active(self) -> bool:
        return datetime.now(timezone.utc).replace(tzinfo=None) < self.expires_at.replace(tzinfo=None)

    def to_dict(self) -> dict:
        return {
            "fail_penalty_pct": self.fail_penalty_pct,
            "expires_at":       self.expires_at.isoformat(),
            "is_active":        self.is_active,
        }
