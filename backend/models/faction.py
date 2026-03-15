"""
models/faction.py — Reputace hráče s frakcí (jeden záznam na postavu)
"""
import json
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base


class FactionReputation(Base):
    __tablename__ = "faction_reputation"

    id:           Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), unique=True)
    faction:      Mapped[str] = mapped_column(String(32))
    reputation:   Mapped[int] = mapped_column(Integer, default=0)

    # JSON array of claimed tier numbers (integers), e.g. [2, 3]
    claimed_tiers_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON array of titles unlocked via faction rewards, e.g. ["Popelový Válečník"]
    unlocked_titles_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    character = relationship("Character", back_populates="faction_reputation")

    # ── Helpers ────────────────────────────────────────────────────────────────
    def get_claimed_tiers(self) -> list[int]:
        if not self.claimed_tiers_json:
            return []
        return json.loads(self.claimed_tiers_json)

    def set_claimed_tiers(self, tiers: list[int]) -> None:
        self.claimed_tiers_json = json.dumps(tiers)

    def get_unlocked_titles(self) -> list[str]:
        if not self.unlocked_titles_json:
            return []
        return json.loads(self.unlocked_titles_json)

    def add_unlocked_title(self, title: str) -> None:
        titles = self.get_unlocked_titles()
        if title not in titles:
            titles.append(title)
        self.unlocked_titles_json = json.dumps(titles)

    def to_dict(self, faction_info: dict) -> dict:
        from game.factions import RENOWN_TIERS, FACTION_REWARDS, get_current_tier, get_next_tier

        rep     = self.reputation
        current = get_current_tier(rep)
        nxt     = get_next_tier(rep)
        claimed = self.get_claimed_tiers()

        tiers = []
        for tier_id, min_rep, name in RENOWN_TIERS:
            reward = FACTION_REWARDS.get(self.faction, {}).get(tier_id)
            tiers.append({
                "tier":      tier_id,
                "name":      name,
                "min_rep":   min_rep,
                "unlocked":  rep >= min_rep,
                "claimed":   tier_id in claimed,
                "reward":    reward,
                # Tier 1 nemá odměnu — ostatní jsou claimovatelné pokud odemčeny a nesebrané
                "claimable": rep >= min_rep and tier_id not in claimed and tier_id > 1,
            })

        return {
            "faction":          self.faction,
            "faction_info":     faction_info,
            "reputation":       rep,
            "current_tier":     current,
            "next_tier":        nxt,
            "progress_to_next": (rep - current["min_rep"]) if nxt else 0,
            "needed_for_next":  (nxt["min_rep"] - current["min_rep"]) if nxt else 0,
            "tiers":            tiers,
            "unlocked_titles":  self.get_unlocked_titles(),
        }
