# backend/models/playtest_run.py
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database import Base

class PlaytestRun(Base):
    __tablename__ = "playtest_runs"

    id:             Mapped[int]            = mapped_column(primary_key=True)
    char_id:        Mapped[int]            = mapped_column(Integer, ForeignKey("characters.id"), index=True)
    dungeon_key:    Mapped[str]            = mapped_column(String(32))
    # "pt_tomb" | "pt_fiery" | "pt_citadel" — prefix pt_ odlišuje od starého systému
    status:         Mapped[str]            = mapped_column(String(16), default="active")
    # "active" | "completed" | "failed"
    map_data:       Mapped[str | None]     = mapped_column(Text, nullable=True)
    # JSON string: {nodes: {...}, edges: [...], layout: {...}}
    current_node_id: Mapped[str | None]   = mapped_column(String(32), nullable=True)
    visited_nodes:  Mapped[str | None]    = mapped_column(Text, nullable=True)
    # JSON string: list of node IDs
    relics:         Mapped[str | None]    = mapped_column(Text, nullable=True)
    # JSON string: [{id, name, effect_key, value, consumed?}]
    pending_relics: Mapped[str | None]    = mapped_column(Text, nullable=True)
    # JSON string: 3 relic nabídky čekající na choose-relic
    hp_current:     Mapped[int]           = mapped_column(Integer, default=0)
    hp_max:         Mapped[int]           = mapped_column(Integer, default=0)
    run_gold:       Mapped[int]           = mapped_column(Integer, default=0)
    reward_xp:      Mapped[int]           = mapped_column(Integer, default=0)
    reward_gold:    Mapped[int]           = mapped_column(Integer, default=0)
    reward_claimed: Mapped[bool]          = mapped_column(Boolean, default=False)
    cooldown_until: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow)

    character = relationship("Character")

    def get_map(self) -> dict:
        import json
        return json.loads(self.map_data) if self.map_data else {}

    def set_map(self, data: dict):
        import json
        self.map_data = json.dumps(data)

    def get_relics(self) -> list:
        import json
        return json.loads(self.relics) if self.relics else []

    def set_relics(self, data: list):
        import json
        self.relics = json.dumps(data)

    def get_visited(self) -> list:
        import json
        return json.loads(self.visited_nodes) if self.visited_nodes else []

    def get_pending_relics(self) -> list:
        import json
        return json.loads(self.pending_relics) if self.pending_relics else []

    def set_pending_relics(self, data: list):
        import json
        self.pending_relics = json.dumps(data)
