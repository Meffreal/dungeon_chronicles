"""
models/soulforger.py — Dušekoval: logy forge operací a správa forge slotů
"""
import json
from datetime import datetime, timedelta
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base

# ── Konstanty ─────────────────────────────────────────────────────────────────

FORGE_SLOT_COUNT     = 3     # Dušekoval má 3 forge sloty
FORGE_COOLDOWN_HOURS = 4     # každý slot se uvolní 4h po použití

# XP za úspěšný forge podle rarity výsledku
FORGE_XP = {
    "common":    30,
    "uncommon":  80,
    "rare":      200,
    "epic":      500,
    "legendary": 1500,
}

FORGE_SALE_BONUS_MULTIPLIER = 0.5   # zpětný bonus XP za prodej = 50 % původního XP

# Šance na selhání forge podle ranku Dušekovale (index = rank)
# Rank 0 nemůže forgovat, Rank 5 nikdy neselhává
FORGE_FAIL_CHANCE = [1.0, 0.30, 0.15, 0.08, 0.02, 0.0]

# Procedurální jména – prefixes a suffixy pro vygenerovaná jména předmětů
FORGE_NAME_PREFIXES = [
    "Zkažený", "Prokletý", "Věčný", "Temný", "Ohnivý", "Stínový",
    "Zpustošený", "Znovuzrozený", "Zlomený", "Krvavý", "Prázdný", "Mlžný",
]
FORGE_NAME_SUFFIXES = [
    "Pádu", "Propasti", "Věčnosti", "Stínů", "Plamenů", "Prázdnoty",
    "Osudu", "Zkázy", "Znovuzrození", "Krve", "Noci", "Posledního Dechu",
]


# ── Model ─────────────────────────────────────────────────────────────────────

class ForgeLog(Base):
    """
    Záznam každé forge operace. Vstupy (inventory itemy) jsou zničeny,
    výstup je nový item v inventáři Dušekovale (nebo prázdný při neúspěchu).

    Procedurální jméno výstupního předmětu se generuje ze vstupů a ukládá sem.
    Retroaktivní XP za prodej: pokud buyer prodá forged item na marketu,
    systém najde ForgeLog podle output_item_id a přidá sale_bonus_xp_awarded = True.
    """
    __tablename__ = "forge_logs"

    id:              Mapped[int] = mapped_column(primary_key=True)
    crafter_char_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"))

    # Vstupy – JSON pole inventory.id (zachováno pro auditní účely po jejich zničení)
    input_inv_ids_json:   Mapped[str] = mapped_column(Text)   # [12, 34, 7]
    # Rarity vstupů – zachováno pro výpočet XP a generování výstupu
    input_rarities_json:  Mapped[str] = mapped_column(Text)   # ["rare", "epic"]

    # Výstup
    output_item_id:   Mapped[int | None] = mapped_column(Integer, ForeignKey("items.id"), nullable=True)
    output_rarity:    Mapped[str | None] = mapped_column(String(16), nullable=True)
    output_name:      Mapped[str | None] = mapped_column(String(128), nullable=True)  # procedurální jméno
    output_flavor:    Mapped[str | None] = mapped_column(Text, nullable=True)          # flavor text z kombinace histórií

    success:          Mapped[bool] = mapped_column(Boolean, default=True)

    # Forge slot (0–2) a cooldown tracking
    forge_slot:       Mapped[int]      = mapped_column(Integer, default=0)
    created_at:       Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # XP tracking
    base_xp:                 Mapped[int]  = mapped_column(Integer, default=0)
    base_xp_awarded:         Mapped[bool] = mapped_column(Boolean, default=False)
    sale_bonus_xp_awarded:   Mapped[bool] = mapped_column(Boolean, default=False)   # retroaktivní

    crafter     = relationship("Character", foreign_keys=[crafter_char_id])
    output_item = relationship("Item", foreign_keys=[output_item_id])

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_input_rarities(self) -> list[str]:
        try:
            return json.loads(self.input_rarities_json)
        except Exception:
            return []

    def get_input_inv_ids(self) -> list[int]:
        try:
            return json.loads(self.input_inv_ids_json)
        except Exception:
            return []

    @property
    def slot_available_at(self) -> datetime:
        """Kdy se tento forge slot uvolní pro další použití."""
        return self.created_at.replace(tzinfo=None) + timedelta(hours=FORGE_COOLDOWN_HOURS)

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "input_rarities":  self.get_input_rarities(),
            "output_rarity":   self.output_rarity,
            "output_name":     self.output_name,
            "output_flavor":   self.output_flavor,
            "success":         self.success,
            "forge_slot":      self.forge_slot,
            "created_at":      self.created_at.isoformat(),
            "slot_available_at": self.slot_available_at.isoformat(),
        }
