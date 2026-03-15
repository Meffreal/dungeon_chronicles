"""
models/dungeon_run.py — Dungeon run model pro multi-stage souboje.

Dungeon = sekvence soubojů (stagů) s přenosem HP mezi stagy.
- Každý stage je generovaný enemy se škálujícím obtíže
- Stage 3 = mini-boss se status efekty
- Stage 5 = final boss s phase transitions
- HP se přenáší (žádná obnova mezi stagy)
- Cooldown 24h
"""
import json
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

from game.combat_engine import BossPhase


# ── Definice dungeonů ──────────────────────────────────────────────────────────
DUNGEON_DEFINITIONS = {
    "tomb_of_forgotten": {
        "id":          "tomb_of_forgotten",
        "name":        "Hrobka Zapomenutých",
        "emoji":       "🪦",
        "description": "Prokletá hrobka plná nemrtvých. Pět stagů až k Strážci Věčnosti.",
        "min_level":   8,
        "cooldown_hours": 8,
        "stages": [
            {
                "stage_num": 1,
                "name":      "Vstupní předsíň",
                "enemy_name": "Kostlivec Stráž",
                "enemy_mult": 0.7,
                "type":      "normal",
            },
            {
                "stage_num": 2,
                "name":      "Hrobová chodba",
                "enemy_name": "Zahnívající Ghúl",
                "enemy_mult": 0.85,
                "type":      "normal",
            },
            {
                "stage_num": 3,
                "name":      "Krypta Rituálů",
                "enemy_name": "Nekromant",
                "enemy_mult": 1.1,
                "type":      "miniboss",
                "special_abilities": ["venomous_bite"],
            },
            {
                "stage_num": 4,
                "name":      "Komnata Prázdnoty",
                "enemy_name": "Stínový Assassin",
                "enemy_mult": 1.25,
                "type":      "elite",
                "special_abilities": ["soul_drain"],
            },
            {
                "stage_num": 5,
                "name":      "Síň Věčnosti",
                "enemy_name": "Strážce Věčnosti",
                "enemy_mult": 2.0,
                "type":      "boss",
                "special_abilities": ["bone_shatter", "soul_drain"],
                "phases": [
                    BossPhase(
                        phase_num=1, trigger_hp_pct=0.60,
                        message="Strážce Věčnosti aktivuje svůj kostěný štít!",
                        stat_multipliers={"def": 1.4},
                    ),
                    BossPhase(
                        phase_num=2, trigger_hp_pct=0.25,
                        message="FINÁLNÍ FÁZE! Strážce Věčnosti uvolňuje plnou sílu prokletí!",
                        stat_multipliers={"atk": 1.8, "spd": 1.3},
                        apply_status_to_player="stun",
                    ),
                ],
            },
        ],
        "rewards": {
            "xp_per_stage":   [100, 150, 250, 350, 600],
            "gold_per_stage":  [50,  80, 130, 180, 400],
            "completion_xp":  800,
            "completion_gold": 500,
        },
    },
    "fiery_depths": {
        "id":          "fiery_depths",
        "name":        "Ohnivé Útroby",
        "emoji":       "🌋",
        "description": "Sopečný dungeon se salamandry a ohnivými duchy. Guardián čeká dole.",
        "min_level":   15,
        "cooldown_hours": 12,
        "stages": [
            {
                "stage_num": 1,
                "name":      "Lávové tunely",
                "enemy_name": "Ohnivý Salamander",
                "enemy_mult": 0.75,
                "type":      "normal",
            },
            {
                "stage_num": 2,
                "name":      "Vulkánická jeskyně",
                "enemy_name": "Magmový Golem",
                "enemy_mult": 0.90,
                "type":      "normal",
            },
            {
                "stage_num": 3,
                "name":      "Chrám Ohně",
                "enemy_name": "Ohnivý Kněz",
                "enemy_mult": 1.15,
                "type":      "miniboss",
                "special_abilities": ["fire_breath"],
            },
            {
                "stage_num": 4,
                "name":      "Sopečná komnata",
                "enemy_name": "Dračí Elita",
                "enemy_mult": 1.35,
                "type":      "elite",
                "special_abilities": ["fire_breath", "bone_shatter"],
            },
            {
                "stage_num": 5,
                "name":      "Srdce sopky",
                "enemy_name": "Strážce Magmy",
                "enemy_mult": 2.2,
                "type":      "boss",
                "special_abilities": ["fire_breath", "chaos_bolt"],
                "phases": [
                    BossPhase(
                        phase_num=1, trigger_hp_pct=0.65,
                        message="Strážce Magmy se ponoří do lávy! Vychází ohnivý hněv!",
                        stat_multipliers={"atk": 1.3},
                        apply_status_to_player="burn",
                    ),
                    BossPhase(
                        phase_num=2, trigger_hp_pct=0.30,
                        message="ERUPCE! Strážce Magmy exploduje ohnivou energií!",
                        stat_multipliers={"atk": 1.8, "spd": 1.4},
                        apply_status_to_player="weaken",
                        heal_pct=0.12,
                    ),
                ],
            },
        ],
        "rewards": {
            "xp_per_stage":   [200, 300, 500, 700, 1200],
            "gold_per_stage":  [100, 150, 250, 350, 700],
            "completion_xp":  1800,
            "completion_gold": 1200,
        },
    },
    "citadel_of_chaos": {
        "id":          "citadel_of_chaos",
        "name":        "Citadela Chaosu",
        "emoji":       "🌀",
        "description": "Transcendentální bašta chaotické energie. Pán Chaosu vládne uvnitř.",
        "min_level":   24,
        "cooldown_hours": 20,
        "stages": [
            {
                "stage_num": 1,
                "name":      "Vstupní portál",
                "enemy_name": "Chaosová Bytost",
                "enemy_mult": 0.80,
                "type":      "normal",
            },
            {
                "stage_num": 2,
                "name":      "Zlomená dimenze",
                "enemy_name": "Dimenzionální Průzkumník",
                "enemy_mult": 1.0,
                "type":      "normal",
            },
            {
                "stage_num": 3,
                "name":      "Chaotický chrám",
                "enemy_name": "Herold Chaosu",
                "enemy_mult": 1.25,
                "type":      "miniboss",
                "special_abilities": ["chaos_bolt"],
            },
            {
                "stage_num": 4,
                "name":      "Věž nicoty",
                "enemy_name": "Protodinatorní Strážce",
                "enemy_mult": 1.5,
                "type":      "elite",
                "special_abilities": ["chaos_bolt", "soul_drain"],
            },
            {
                "stage_num": 5,
                "name":      "Trůnní síň Chaosu",
                "enemy_name": "Pán Chaosu",
                "enemy_mult": 2.5,
                "type":      "boss",
                "special_abilities": ["chaos_bolt", "soul_drain", "fire_breath"],
                "phases": [
                    BossPhase(
                        phase_num=1, trigger_hp_pct=0.70,
                        message="Pán Chaosu otevírá průrvu nicoty!",
                        stat_multipliers={"spd": 1.4},
                        apply_status_to_player="slow",
                    ),
                    BossPhase(
                        phase_num=2, trigger_hp_pct=0.40,
                        message="CHAOS DIMENSION! Pán Chaosu mění pravidla reality!",
                        stat_multipliers={"atk": 1.5, "spd": 1.5},
                        apply_status_to_player="weaken",
                    ),
                    BossPhase(
                        phase_num=3, trigger_hp_pct=0.15,
                        message="TOTÁLNÍ CHAOS! Pán Chaosu uvolňuje veškerou svou destruktivní moc!",
                        stat_multipliers={"atk": 2.2, "spd": 2.0},
                        apply_status_to_player="stun",
                        heal_pct=0.20,
                    ),
                ],
            },
        ],
        "rewards": {
            "xp_per_stage":   [400, 600, 1000, 1400, 2500],
            "gold_per_stage":  [200, 300, 500,  700,  1500],
            "completion_xp":  4000,
            "completion_gold": 2500,
        },
    },
}


class DungeonRun(Base):
    """Aktivní nebo dokončený dungeon run hráče."""
    __tablename__ = "dungeon_runs"

    id:            Mapped[int]          = mapped_column(primary_key=True)
    character_id:  Mapped[int]          = mapped_column(Integer, ForeignKey("characters.id"), index=True)
    dungeon_key:   Mapped[str]          = mapped_column(String(32))

    current_stage: Mapped[int]          = mapped_column(Integer, default=1)
    total_stages:  Mapped[int]          = mapped_column(Integer, default=5)
    player_hp_current: Mapped[int]      = mapped_column(Integer, default=0)
    player_hp_max: Mapped[int]          = mapped_column(Integer, default=0)

    status:        Mapped[str]          = mapped_column(String(16), default="active")
    # "active" | "completed" | "failed" | "idle"

    started_at:    Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_stage_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at:  Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Cooldown pro tento dungeon typ (uložíme datum posledního dokončení)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Kumulativní odměny za dokončené stagy (inkrement při každém dokončeném stage)
    reward_xp:    Mapped[int]           = mapped_column(Integer, default=0)
    reward_gold:  Mapped[int]           = mapped_column(Integer, default=0)
    reward_claimed: Mapped[bool]        = mapped_column(Boolean, default=False)

    # Secret path (stage 3 branching)
    secret_path_offered: Mapped[bool]   = mapped_column(Boolean, default=False)
    secret_path_taken:   Mapped[bool]   = mapped_column(Boolean, default=False)

    # Battle logy všech stagů (JSON array of log arrays)
    stage_logs_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    character = relationship("Character")

    def get_stage_logs(self) -> list:
        """Vrátí logy všech stagů."""
        if not self.stage_logs_json:
            return []
        try:
            return json.loads(self.stage_logs_json)
        except Exception:
            return []

    def append_stage_log(self, stage_num: int, log: list, events: list):
        """Přidá log dalšího stage."""
        logs = self.get_stage_logs()
        logs.append({
            "stage_num": stage_num,
            "log":       log,
            "events":    events,
        })
        self.stage_logs_json = json.dumps(logs, ensure_ascii=False)

    def to_dict(self) -> dict:
        ddef = DUNGEON_DEFINITIONS.get(self.dungeon_key, {})
        stages = ddef.get("stages", [])
        current_stage_def = next(
            (s for s in stages if s["stage_num"] == self.current_stage), None
        )
        return {
            "id":              self.id,
            "dungeon_key":     self.dungeon_key,
            "dungeon_name":    ddef.get("name", self.dungeon_key),
            "dungeon_emoji":   ddef.get("emoji", "🗝"),
            "current_stage":   self.current_stage,
            "total_stages":    self.total_stages,
            "player_hp_current": self.player_hp_current,
            "player_hp_max":   self.player_hp_max,
            "player_hp_pct":   round(self.player_hp_current / max(1, self.player_hp_max) * 100, 1),
            "status":          self.status,
            "reward_xp":       self.reward_xp,
            "reward_gold":     self.reward_gold,
            "reward_claimed":  self.reward_claimed,
            "cooldown_until":  self.cooldown_until.isoformat() if self.cooldown_until else None,
            "current_stage_name": current_stage_def["name"] if current_stage_def else "",
            "stage_logs":         self.get_stage_logs(),
            "secret_path_offered": self.secret_path_offered,
            "secret_path_taken":   self.secret_path_taken,
        }
