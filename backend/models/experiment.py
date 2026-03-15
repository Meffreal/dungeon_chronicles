"""
models/experiment.py — A/B testing framework pro balance experimenty.

Každý hráč dostane experiment_group (0–9) při vytvoření postavy.
Admin definuje experimenty: která skupina → jaké override hodnoty.
Combat engine + routery čtou overrides a aplikují je pro danou skupinu.
"""
import json
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from database import Base

# ── Balancovatelné konstanty (klíče pro override dict) ───────────────────────
OVERRIDABLE_PARAMS = {
    # Combat engine
    "ability_trigger_prob": {
        "label": "Šance triggeru ability",
        "default": 0.40,
        "unit": "%",
        "description": "Pravděpodobnost spuštění class ability (default 40%).",
        "range": [0.10, 0.80],
    },
    "crit_damage_mult": {
        "label": "Multiplier critu",
        "default": 1.75,
        "unit": "×",
        "description": "Kolik násobků normálního poškození způsobí crit (default ×1.75).",
        "range": [1.10, 3.00],
    },
    "ability_damage_mult": {
        "label": "Multiplier poškození ability",
        "default": 1.00,
        "unit": "×",
        "description": "Globální škálovač poškození všech class abilities.",
        "range": [0.50, 2.00],
    },
    # Quest routery
    "gold_reward_win": {
        "label": "Gold z výhry v aréně",
        "default": 1.00,
        "unit": "×",
        "description": "Multiplikátor gold odměny za výhru v aréně.",
        "range": [0.50, 3.00],
    },
    "xp_reward_mult": {
        "label": "Multiplikátor XP z questů",
        "default": 1.00,
        "unit": "×",
        "description": "Globální škálovač XP odměn z questů.",
        "range": [0.50, 3.00],
    },
    "dodge_chance_cap": {
        "label": "Cap šance na dodge",
        "default": 0.35,
        "unit": "%",
        "description": "Maximální šance na uhnutí (default 35%).",
        "range": [0.10, 0.60],
    },
}


class Experiment(Base):
    """
    A/B experiment — mapuje skupiny hráčů na override hodnoty.
    group_start a group_end definují uzavřený interval skupin [group_start, group_end].
    Hráči v tomto rozsahu dostanou override hodnoty místo defaultů.
    """
    __tablename__ = "experiments"

    id:          Mapped[int] = mapped_column(primary_key=True)
    name:        Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")

    # Skupiny hráčů, na které se experiment vztahuje (0–9 každá)
    group_start: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    group_end:   Mapped[int] = mapped_column(Integer, default=4, server_default="4")

    # Override hodnoty jako JSON dict: {"ability_trigger_prob": 0.30, "gold_reward_win": 1.5, ...}
    override_json: Mapped[str] = mapped_column(Text, default="{}", server_default="{}")

    is_active:  Mapped[bool]     = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def get_overrides(self) -> dict:
        """Vrátí override hodnoty jako dict."""
        try:
            return json.loads(self.override_json) if self.override_json else {}
        except Exception:
            return {}

    def set_overrides(self, overrides: dict):
        self.override_json = json.dumps(overrides)

    def applies_to_group(self, group: int) -> bool:
        """Vrátí True pokud se experiment vztahuje na danou skupinu."""
        return self.group_start <= group <= self.group_end

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "group_start": self.group_start,
            "group_end":   self.group_end,
            "groups":      list(range(self.group_start, self.group_end + 1)),
            "overrides":   self.get_overrides(),
            "is_active":   self.is_active,
            "created_at":  self.created_at.isoformat() if self.created_at else None,
        }
