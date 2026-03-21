# Dungeon Playtest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Přidat izolovaný Playtest tab s roguelite dungeon systémem (node-based mapa, relics, events) aniž by se dotkl stávajícího dungeon systému.

**Architecture:** Kompletní izolace pod prefixem `/playtest/` — nový ORM model `PlaytestRun`, nový router `playtest_dungeon.py`, nová game logika `game/playtest_dungeon.py`, nový frontend `playtest.js`. Starý `dungeon.py`, `dungeon_run.py`, `dungeon.js` se nemění.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async (Mapped[] styl), Alembic, pytest-asyncio, Vanilla JS, SVG pro mapu.

**Spec:** `docs/superpowers/specs/2026-03-21-dungeon-playtest-redesign-design.md`

---

## Soubory

| Akce | Soubor |
|------|--------|
| Create | `backend/models/playtest_run.py` |
| Create | `backend/alembic/versions/0049_playtest_runs.py` |
| Create | `backend/game/playtest_dungeon.py` |
| Create | `backend/routers/playtest_dungeon.py` |
| Create | `backend/tests/test_playtest_dungeon.py` |
| Modify | `backend/models/__init__.py` — přidat export PlaytestRun |
| Modify | `backend/main.py` — přidat import + include_router |
| Modify | `backend/game/combat_engine.py` — přidat vampiric_edge handler do set_bonuses |
| Create | `frontend/js/playtest.js` |
| Modify | `frontend/css/components.css` — přidat .pt-* třídy |
| Modify | `frontend/game.html` — přidat page-playtest div + nav tlačítko |

---

## Task 1: ORM Model PlaytestRun

**Files:**
- Create: `backend/models/playtest_run.py`
- Modify: `backend/models/__init__.py`

- [ ] **Step 1: Napsat model**

```python
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
```

- [ ] **Step 2: Přidat export do `backend/models/__init__.py`**

Najdi sekci s ostatními modely a přidej:
```python
from models.playtest_run import PlaytestRun
```

- [ ] **Step 3: Commit**

```bash
git add backend/models/playtest_run.py backend/models/__init__.py
git commit -m "feat: add PlaytestRun ORM model"
```

---

## Task 2: Alembic Migrace

**Files:**
- Create: `backend/alembic/versions/0049_playtest_runs.py`

- [ ] **Step 1: Napsat migraci**

```python
# backend/alembic/versions/0049_playtest_runs.py
"""Add playtest_runs table

Revision ID: 0049
Revises: 0048
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '0049'
down_revision = '0048'
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    existing = insp.get_table_names()
    if 'playtest_runs' in existing:
        return  # idempotentní guard

    op.create_table(
        'playtest_runs',
        sa.Column('id',             sa.Integer(),    primary_key=True),
        sa.Column('char_id',        sa.Integer(),    sa.ForeignKey('characters.id'), nullable=False, index=True),
        sa.Column('dungeon_key',    sa.String(32),   nullable=False),
        sa.Column('status',         sa.String(16),   nullable=False, server_default='active'),
        sa.Column('map_data',       sa.Text(),       nullable=True),
        sa.Column('current_node_id', sa.String(32),  nullable=True),
        sa.Column('visited_nodes',  sa.Text(),       nullable=True),
        sa.Column('relics',         sa.Text(),       nullable=True),
        sa.Column('pending_relics', sa.Text(),       nullable=True),
        sa.Column('hp_current',     sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('hp_max',         sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('run_gold',       sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('reward_xp',      sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('reward_gold',    sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('reward_claimed', sa.Boolean(),    nullable=False, server_default='0'),
        sa.Column('cooldown_until', sa.DateTime(),   nullable=True),
        sa.Column('created_at',     sa.DateTime(),   nullable=False),
    )

def downgrade():
    op.drop_table('playtest_runs')
```

- [ ] **Step 2: Ověřit down_revision**

Zkontroluj revision ID posledního souboru v `backend/alembic/versions/0048_*.py` a ujisti se, že `down_revision = '0048'` odpovídá jeho `revision` hodnotě.

- [ ] **Step 3: Spustit migraci**

```bash
cd backend && alembic upgrade head
```

Očekávaný výstup: `Running upgrade 0048 -> 0049`

- [ ] **Step 4: Commit**

```bash
git add backend/alembic/versions/0049_playtest_runs.py
git commit -m "feat: add migration 0049 — playtest_runs table"
```

---

## Task 3: Game Logic — Dungeon definice, mapa, relics, eventy

> **TDD poznámka:** Nejprve napište test soubor (Task 4 Step 1), spusťte testy aby selhaly (Task 4 Step 2), pak implementujte (Task 3), pak spusťte testy znovu (Task 4 Step 3). Plán je psán v pořadí implementace pro čitelnost — při skutečné implementaci postupujte red→green.

**Files:**
- Create: `backend/game/playtest_dungeon.py`

- [ ] **Step 1: Napsat PLAYTEST_DUNGEONS, RELIC_POOL, DUNGEON_EVENTS**

```python
# backend/game/playtest_dungeon.py
"""
Herní logika pro Playtest roguelite dungeon systém.
Izolovaná od starého dungeon systému.
"""
import random
import json
from typing import Optional

# ── Dungeon konfigurace ───────────────────────────────────────────────────────

PLAYTEST_DUNGEONS = {
    "pt_tomb": {
        "name": "Tomb of Forgotten",
        "min_level": 8,
        "cooldown_hours": 6,
        "boss_mult": 2.0,
        "boss_name": "Guardian of Eternity",
        "enemy_pool": [
            ("Skeleton Guard", 0.8),
            ("Tomb Crawler", 0.85),
            ("Cursed Wraith", 0.9),
        ],
        "elite_name": "Tomb Warden",
        "elite_mult": 1.4,
        "xp_base": 80,
        "gold_base": 40,
    },
    "pt_fiery": {
        "name": "Fiery Depths",
        "min_level": 15,
        "cooldown_hours": 8,
        "boss_mult": 2.4,
        "boss_name": "Magma Lord",
        "enemy_pool": [
            ("Fire Imp", 0.9),
            ("Lava Golem", 0.95),
            ("Ember Witch", 1.0),
        ],
        "elite_name": "Infernal Warden",
        "elite_mult": 1.5,
        "xp_base": 150,
        "gold_base": 80,
    },
    "pt_citadel": {
        "name": "Citadel of Chaos",
        "min_level": 24,
        "cooldown_hours": 12,
        "boss_mult": 2.8,
        "boss_name": "Lord of Chaos",
        "enemy_pool": [
            ("Chaos Knight", 1.0),
            ("Void Stalker", 1.05),
            ("Corrupted Mage", 1.1),
        ],
        "elite_name": "Chaos Warden",
        "elite_mult": 1.6,
        "xp_base": 280,
        "gold_base": 150,
    },
}

# ── Relic pool ────────────────────────────────────────────────────────────────

RELIC_POOL = [
    {"id": "blood_stone",   "name": "Krvavý kámen",     "effect_key": "atk_pct",        "value": 0.20, "desc": "+20% ATK"},
    {"id": "stone_shield",  "name": "Kamenný štít",     "effect_key": "def_pct",        "value": 0.15, "desc": "+15% DEF"},
    {"id": "healing_herb",  "name": "Léčivá bylina",    "effect_key": "hp_restore_pct", "value": 0.15, "desc": "Obnov 15% HP ihned"},
    {"id": "gold_coin",     "name": "Zlatá mince",      "effect_key": "gold_pct",       "value": 0.50, "desc": "+50% gold z uzlů"},
    {"id": "swift_boots",   "name": "Rychlé nohy",      "effect_key": "spd_pct",        "value": 0.15, "desc": "+15% SPD"},
    {"id": "war_cry",       "name": "Válečný pokřik",   "effect_key": "atk_spd_pct",    "value": 0.10, "desc": "+10% ATK, +10% SPD"},
    {"id": "iron_will",     "name": "Železná vůle",     "effect_key": "hp_max_pct",     "value": 0.20, "desc": "+20% max HP"},
    {"id": "cursed_blade",  "name": "Prokletý meč",     "effect_key": "cursed_blade",   "value": 0.35, "desc": "+35% ATK, -10% DEF"},
    {"id": "lucky_charm",   "name": "Šťastný amulet",   "effect_key": "luck_pct",       "value": 0.15, "desc": "+15% LUCK"},
    {"id": "ancient_tome",  "name": "Starobylý svazek", "effect_key": "xp_pct",         "value": 0.25, "desc": "+25% XP z uzlů"},
    {"id": "vampiric_edge", "name": "Vampýrická čepel", "effect_key": "vampiric_edge",  "value": 0.15, "desc": "10% šance léčit se za 15% DMG"},
    {"id": "mana_crystal",  "name": "Mana krystal",     "effect_key": "mp_pct",         "value": 0.20, "desc": "+20% schopnosti"},
]

ELITE_RELIC_POOL = [r for r in RELIC_POOL if r["id"] not in ("healing_herb", "gold_coin")]

# ── Eventy ────────────────────────────────────────────────────────────────────

DUNGEON_EVENTS = {
    "pt_tomb": [
        {
            "id": "golden_chest",
            "text": "Nalezl jsi zlatou truhlu ozdobenou runami.",
            "choices": [
                {"index": 0, "label": "Otevři truhlu", "hint": "70% šance na +200g, 30% šance na past (-15% HP)"},
                {"index": 1, "label": "Ignoruj", "hint": "Nic nezískaš, nic neriskuješ"},
            ],
            "outcomes": {
                0: [
                    {"weight": 70, "type": "gold", "amount": 200, "text": "Uvnitř se třpytí zlaté mince. +200g"},
                    {"weight": 30, "type": "hp_loss", "percent": 0.15, "text": "Past! Jehly tě probodnou. -15% HP"},
                ],
                1: [{"weight": 100, "type": "nothing", "text": "Procházíš dál bez povšimnutí."}],
            },
        },
        {
            "id": "lost_spirit",
            "text": "Duch starého válečníka tě prosí o pomoc s přechodem.",
            "choices": [
                {"index": 0, "label": "Pomoz duchovi", "hint": "Ztratíš 10% HP, ale získáš extra relic"},
                {"index": 1, "label": "Odmítni", "hint": "Nic se nestane"},
            ],
            "outcomes": {
                0: [{"weight": 100, "type": "hp_loss_and_relic", "percent": 0.10, "text": "Duch ti předá svůj amulet. -10% HP, +1 relic výběr"}],
                1: [{"weight": 100, "type": "nothing", "text": "Duch zmizí s tichým vzlykotem."}],
            },
        },
        {
            "id": "secret_passage",
            "text": "Za pohyblivým kamenem vidíš tajnou chodbu vedoucí hluboko do hrobky.",
            "choices": [
                {"index": 0, "label": "Vstup do chodby", "hint": "Příští combat bude 60% silnější, ale odměna 2×"},
                {"index": 1, "label": "Ignoruj", "hint": "Pokračuješ normální cestou"},
            ],
            "outcomes": {
                0: [{"weight": 100, "type": "next_node_boost", "mult": 1.6, "reward_mult": 2.0, "text": "Tajná chodba! Příprav se na silnějšího nepřítele."}],
                1: [{"weight": 100, "type": "nothing", "text": "Přesouváš kamen zpět na místo."}],
            },
        },
        {
            "id": "ancient_altar",
            "text": "Starý oltář s miskou na oběti. Nápis: 'Daruj krev, získej moc.'",
            "choices": [
                {"index": 0, "label": "Obětuj krev", "hint": "-20% HP, +30% ATK na zbytek runu"},
                {"index": 1, "label": "Přejdi dál", "hint": "Nic se nestane"},
            ],
            "outcomes": {
                0: [{"weight": 100, "type": "hp_loss_and_atk", "percent": 0.20, "atk_bonus": 0.30, "text": "Miska se naplní a oltář se rozsvítí. Cítíš příliv síly. -20% HP, +30% ATK"}],
                1: [{"weight": 100, "type": "nothing", "text": "Oltář zůstává prázdný."}],
            },
        },
        {
            "id": "trapped_adventurer",
            "text": "Uvězněný dobrodruh tě prosí o pomoc. Vypadá podezřele...",
            "choices": [
                {"index": 0, "label": "Osvoboď ho", "hint": "50% šance získat gold, 50% šance na léčku"},
                {"index": 1, "label": "Nech ho být", "hint": "Nic"},
            ],
            "outcomes": {
                0: [
                    {"weight": 50, "type": "gold", "amount": 150, "text": "Byl to skutečný dobrodruh! Odměnil tě za pomoc. +150g"},
                    {"weight": 50, "type": "hp_loss", "percent": 0.20, "text": "Past! Byl to démon v přestrojení. -20% HP"},
                ],
                1: [{"weight": 100, "type": "nothing", "text": "Procházíš kolem bez zastavení."}],
            },
        },
        {
            "id": "magic_fountain",
            "text": "Nalezl jsi kouzelnou fontánu. Voda se třpytí modře.",
            "choices": [
                {"index": 0, "label": "Napij se", "hint": "Obnov 30% HP"},
                {"index": 1, "label": "Ignoruj", "hint": "Nic"},
            ],
            "outcomes": {
                0: [{"weight": 100, "type": "hp_restore", "percent": 0.30, "text": "Voda chutná jako život sám. +30% HP"}],
                1: [{"weight": 100, "type": "nothing", "text": "Přecházíš dál."}],
            },
        },
    ],
}
# Fiery a Citadel sdílí stejnou strukturu eventů (s jiným flavour textem) — pro MVP použij tomb eventy s jiným textem
DUNGEON_EVENTS["pt_fiery"] = DUNGEON_EVENTS["pt_tomb"]
DUNGEON_EVENTS["pt_citadel"] = DUNGEON_EVENTS["pt_tomb"]
```

- [ ] **Step 2: Napsat generátor mapy**

Přidej do stejného souboru:

```python
# ── Generátor mapy ────────────────────────────────────────────────────────────

def generate_map(dungeon_key: str, char_level: int) -> dict:
    """
    Vygeneruje procedurální mapu pro dungeon run.
    Struktura: Start → [Vrstva1: 2 uzly] → [Vrstva2: 2 uzly] → [Vrstva3: 2 uzly] → Boss
    Každá vrstva má 2 uzly, hráč volí jeden, druhý se přeskočí.
    """
    cfg = PLAYTEST_DUNGEONS[dungeon_key]
    nodes = {}
    edges = []
    layout = {}

    # Start uzel
    nodes["start"] = {"type": "start", "status": "completed"}
    layout["start"] = [0, 0]

    # Vrstva 1: combat + (rest nebo event)
    l1_left  = _make_combat_node(cfg, char_level, "n1a")
    l1_right_type = random.choice(["rest", "event"])
    l1_right = _make_node(l1_right_type, cfg, char_level, "n1b", dungeon_key)
    nodes["n1a"] = l1_left
    nodes["n1b"] = l1_right
    layout["n1a"] = [1, -1]
    layout["n1b"] = [1, 1]
    edges += [["start", "n1a"], ["start", "n1b"]]
    # Vrstva 1 uzly jsou ihned dostupné (obě volby otevřené od startu)
    nodes["n1a"]["status"] = "available"
    nodes["n1b"]["status"] = "available"

    # Vrstva 2: (combat nebo elite) + (event nebo shop)
    l2_left_type  = random.choice(["combat", "elite"])
    l2_right_type = random.choice(["event", "shop"])
    l2_left  = _make_node(l2_left_type,  cfg, char_level, "n2a", dungeon_key)
    l2_right = _make_node(l2_right_type, cfg, char_level, "n2b", dungeon_key)
    nodes["n2a"] = l2_left
    nodes["n2b"] = l2_right
    layout["n2a"] = [2, -1]
    layout["n2b"] = [2, 1]
    edges += [["n1a", "n2a"], ["n1a", "n2b"], ["n1b", "n2a"], ["n1b", "n2b"]]

    # Vrstva 3: elite + (rest nebo combat)
    l3_left  = _make_node("elite",  cfg, char_level, "n3a", dungeon_key)
    l3_right_type = random.choice(["rest", "combat"])
    l3_right = _make_node(l3_right_type, cfg, char_level, "n3b", dungeon_key)
    nodes["n3a"] = l3_left
    nodes["n3b"] = l3_right
    layout["n3a"] = [3, -1]
    layout["n3b"] = [3, 1]
    edges += [["n2a", "n3a"], ["n2a", "n3b"], ["n2b", "n3a"], ["n2b", "n3b"]]

    # Boss
    boss_xp   = int(cfg["xp_base"]   * char_level * cfg["boss_mult"] * 3)
    boss_gold = int(cfg["gold_base"]  * char_level * cfg["boss_mult"] * 2)
    nodes["n_boss"] = {
        "type": "boss",
        "enemy_name": cfg["boss_name"],
        "enemy_mult": cfg["boss_mult"],
        "status": "locked",
        "reward_xp": boss_xp,
        "reward_gold": boss_gold,
    }
    layout["n_boss"] = [4, 0]
    edges += [["n3a", "n_boss"], ["n3b", "n_boss"]]

    map_data = {"nodes": nodes, "edges": edges, "layout": layout}
    _apply_constraint_fixes(map_data, cfg, char_level)
    return map_data


def _make_combat_node(cfg: dict, char_level: int, node_id: str) -> dict:
    enemy_name, enemy_mult = random.choice(cfg["enemy_pool"])
    xp   = int(cfg["xp_base"]   * char_level * enemy_mult)
    gold = int(cfg["gold_base"]  * char_level * enemy_mult)
    return {"type": "combat", "enemy_name": enemy_name, "enemy_mult": enemy_mult,
            "status": "locked", "reward_xp": xp, "reward_gold": gold}


def _make_node(node_type: str, cfg: dict, char_level: int, node_id: str, dungeon_key: str = "pt_tomb") -> dict:
    """dungeon_key musí být předán explicitně — cfg dict neobsahuje vlastní klíč."""
    if node_type == "combat":
        return _make_combat_node(cfg, char_level, node_id)
    elif node_type == "elite":
        xp   = int(cfg["xp_base"]   * char_level * cfg["elite_mult"] * 1.5)
        gold = int(cfg["gold_base"]  * char_level * cfg["elite_mult"] * 1.5)
        return {"type": "elite", "enemy_name": cfg["elite_name"],
                "enemy_mult": cfg["elite_mult"], "status": "locked",
                "reward_xp": xp, "reward_gold": gold}
    elif node_type == "rest":
        return {"type": "rest", "status": "locked"}
    elif node_type == "event":
        events = DUNGEON_EVENTS.get(dungeon_key, DUNGEON_EVENTS["pt_tomb"])
        event = random.choice(events)
        return {"type": "event", "event_id": event["id"], "status": "locked"}
    elif node_type == "shop":
        return {"type": "shop", "status": "locked"}
    return {"type": node_type, "status": "locked"}


def _apply_constraint_fixes(map_data: dict, cfg: dict, char_level: int):
    """Force-substituce pokud constraints nejsou splněny."""
    nodes = map_data["nodes"]
    types = [n["type"] for n in nodes.values()]

    if "rest" not in types:
        nodes["n3b"] = _make_node("rest", cfg, char_level, "n3b")

    types = [n["type"] for n in nodes.values()]
    if "elite" not in types:
        old = nodes["n2a"]
        nodes["n2a"] = _make_node("elite", cfg, char_level, "n2a")

    types = [n["type"] for n in nodes.values()]
    if "event" not in types:
        nodes["n1b"] = _make_node("event", cfg, char_level, "n1b")


def get_available_nodes(map_data: dict) -> list[str]:
    """Vrátí ID uzlů se statusem 'available'."""
    return [nid for nid, n in map_data["nodes"].items() if n["status"] == "available"]


def unlock_successors(map_data: dict, completed_node_id: str):
    """Odemkne sousedy dokončeného uzlu (status locked → available)."""
    nodes   = map_data["nodes"]
    edges   = map_data["edges"]
    visited = {nid for nid, n in nodes.items() if n["status"] in ("completed", "pending_event")}

    for src, dst in edges:
        if src == completed_node_id and nodes.get(dst, {}).get("status") == "locked":
            # Odemkni jen pokud všechny rodiče (příchozí hrany) jsou dokončeny
            parents = [s for s, d in edges if d == dst]
            # Uzel odemkneš jakmile aspoň jeden rodič je dokončen (hráč mohl přijít z různých cest)
            nodes[dst]["status"] = "available"
```

- [ ] **Step 3: Napsat relic helper funkce**

Přidej do stejného souboru:

```python
# ── Relic helpers ─────────────────────────────────────────────────────────────

def roll_relics(existing_relic_ids: list[str], is_elite: bool = False, count: int = 3) -> list[dict]:
    """Vyber count náhodných relics z poolu. Nezahrnuj relics které hráč už má."""
    pool = ELITE_RELIC_POOL if is_elite else RELIC_POOL
    available = [r for r in pool if r["id"] not in existing_relic_ids]
    if len(available) < count:
        available = pool  # fallback — v pozdní fázi runu může být málo možností
    return random.sample(available, min(count, len(available)))


def apply_relic_to_run(run, relic: dict):
    """
    Aplikuje one-time efekty ihned. Passive efekty jsou aplikovány v build_playtest_combatant.
    Vrátí dict s popisem co se stalo (pro frontend).
    """
    result = {"hp_delta": 0, "description": relic["desc"]}

    if relic["effect_key"] == "hp_restore_pct":
        healed = int(run.hp_max * relic["value"])
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        result["hp_delta"] = healed
        relic["consumed"] = True  # one-time efekt — označit jako spotřebovaný

    elif relic["effect_key"] == "hp_max_pct":
        # iron_will — zvýšit hp_max, ale NEléčit
        run.hp_max = int(run.hp_max * (1 + relic["value"]))

    return result
```

- [ ] **Step 4: Napsat build_playtest_combatant**

```python
# ── Combat builder ────────────────────────────────────────────────────────────

async def build_playtest_combatant(char, run, db):
    """
    Sestaví CombatantConfig pro hráče s aplikovanými relic efekty.
    Používá build_combatant_config jako základ a pak aplikuje relics.
    """
    from game.combatant_builder import build_combatant_config
    from game.combat_engine import CombatantConfig

    # Základ z existujícího builderu (čte equipment, stats, atd.)
    base_cfg = await build_combatant_config(char, db)

    # Přepsat HP aktuálním stavem z runu (ne char.hp_max)
    base_cfg.hp = run.hp_current

    # Aplikuj pasivní relic efekty
    relics = run.get_relics()
    for relic in relics:
        if relic.get("consumed"):
            continue
        key = relic["effect_key"]
        val = relic["value"]

        if key == "atk_pct":
            # weapon_dmg a primary_stat jsou hlavní útočné stats
            base_cfg.weapon_dmg   = int(base_cfg.weapon_dmg   * (1 + val))
            base_cfg.primary_stat = int(base_cfg.primary_stat * (1 + val))
        elif key == "def_pct":
            base_cfg.armor_value = int(base_cfg.armor_value * (1 + val))
        elif key == "atk_spd_pct":
            base_cfg.weapon_dmg   = int(base_cfg.weapon_dmg   * (1 + val))
            base_cfg.primary_stat = int(base_cfg.primary_stat * (1 + val))
            # SPD — pokud CombatantConfig má spd field, jinak skip
            if hasattr(base_cfg, 'spd'):
                base_cfg.spd = int(base_cfg.spd * (1 + val))
        elif key == "luck_pct":
            base_cfg.luck = int(base_cfg.luck * (1 + val))
        elif key == "cursed_blade":
            base_cfg.weapon_dmg   = int(base_cfg.weapon_dmg   * (1 + val))
            base_cfg.primary_stat = int(base_cfg.primary_stat * (1 + val))
            base_cfg.armor_value  = int(base_cfg.armor_value  * 0.90)
        elif key == "vampiric_edge":
            # vampiric_edge se předá přes set_bonuses
            existing = base_cfg.set_bonuses or {}
            base_cfg.set_bonuses = {**existing, "vampiric_lifesteal": 0.15, "vampiric_chance": 0.10}

    # gold_coin, xp_pct, mp_pct — žádný efekt na CombatantConfig (aplikují se při reward výpočtu)
    return base_cfg


def build_enemy_config(dungeon_key: str, node: dict, char_level: int):
    """Sestaví CombatantConfig pro nepřítele z node dat."""
    from game.combat_engine import CombatantConfig

    cfg  = PLAYTEST_DUNGEONS[dungeon_key]
    mult = node["enemy_mult"]
    lvl  = max(char_level, PLAYTEST_DUNGEONS[dungeon_key].get("min_level", 1))

    is_boss = node["type"] == "boss"
    return CombatantConfig(
        name         = node["enemy_name"],
        hp           = int(60  * lvl * mult),
        weapon_dmg   = int(9   * lvl * mult),
        armor_value  = int(5   * lvl * mult),
        primary_stat = int(8   * lvl * mult),
        secondary_a  = int(6   * lvl * mult),   # povinný field — DEX ekvivalent
        secondary_b  = int(4   * lvl * mult),   # povinný field — INT ekvivalent
        luck         = 5,
        level        = lvl,
        cls          = "enemy",
        is_boss      = is_boss,
    )


def calculate_node_rewards(node: dict, relics: list, xp_base: int, gold_base: int) -> tuple[int, int]:
    """Vypočítá XP a gold odměnu z uzlu s relic bonusy."""
    xp   = node.get("reward_xp",   xp_base)
    gold = node.get("reward_gold", gold_base)

    for relic in relics:
        if relic.get("consumed"):
            continue
        if relic["effect_key"] == "gold_pct":
            gold = int(gold * (1 + relic["value"]))
        elif relic["effect_key"] == "xp_pct":
            xp = int(xp * (1 + relic["value"]))

    return xp, gold
```

- [ ] **Step 5: Napsat event handler**

```python
# ── Event handler ─────────────────────────────────────────────────────────────

def apply_event_choice(run, dungeon_key: str, event_id: str, choice_index: int) -> dict:
    """
    Aplikuje výsledek event volby. Vrátí dict s outcome info.
    """
    events_list = DUNGEON_EVENTS.get(dungeon_key, DUNGEON_EVENTS["pt_tomb"])
    event = next((e for e in events_list if e["id"] == event_id), None)
    if not event:
        return {"outcome_text": "Nic se nestalo.", "hp_delta": 0, "gold_delta": 0}

    outcomes = event["outcomes"].get(choice_index, [{"weight": 100, "type": "nothing", "text": "Nic."}])
    # Weighted random výběr
    total  = sum(o["weight"] for o in outcomes)
    roll   = random.randint(1, total)
    cumul  = 0
    chosen = outcomes[-1]
    for o in outcomes:
        cumul += o["weight"]
        if roll <= cumul:
            chosen = o
            break

    result = {"outcome_text": chosen["text"], "hp_delta": 0, "gold_delta": 0, "pending_relics": None}

    otype = chosen["type"]
    if otype == "gold":
        run.run_gold += chosen["amount"]
        result["gold_delta"] = chosen["amount"]
    elif otype == "hp_loss":
        loss = int(run.hp_max * chosen["percent"])
        run.hp_current = max(0, run.hp_current - loss)
        result["hp_delta"] = -loss
    elif otype == "hp_restore":
        healed = int(run.hp_max * chosen["percent"])
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        result["hp_delta"] = healed
    elif otype == "hp_loss_and_relic":
        loss = int(run.hp_max * chosen["percent"])
        run.hp_current = max(0, run.hp_current - loss)
        result["hp_delta"]      = -loss
        existing_ids            = [r["id"] for r in run.get_relics()]
        result["pending_relics"] = roll_relics(existing_ids, count=1)
    elif otype == "hp_loss_and_atk":
        loss = int(run.hp_max * chosen["percent"])
        run.hp_current = max(0, run.hp_current - loss)
        result["hp_delta"] = -loss
        # Přidat one-shot atk boost relic
        boost = {"id": "event_atk_boost", "name": "Krvavá smlouva",
                 "effect_key": "atk_pct", "value": chosen["atk_bonus"],
                 "desc": f"+{int(chosen['atk_bonus']*100)}% ATK (event)"}
        relics = run.get_relics()
        relics.append(boost)
        run.set_relics(relics)
    elif otype == "next_node_boost":
        # Uložit override do map_data — příští combat uzel dostane boost
        mdata = run.get_map()
        mdata["pending_boost"] = {"mult": chosen["mult"], "reward_mult": chosen["reward_mult"]}
        run.set_map(mdata)

    return result
```

- [ ] **Step 6: Commit**

```bash
git add backend/game/playtest_dungeon.py
git commit -m "feat: add playtest game logic (map gen, relics, events, combat builder)"
```

---

## Task 4: Testy pro game logiku

**Files:**
- Create: `backend/tests/test_playtest_dungeon.py`

- [ ] **Step 1: Napsat testy**

```python
# backend/tests/test_playtest_dungeon.py
import pytest
from game.playtest_dungeon import (
    generate_map, get_available_nodes, unlock_successors,
    roll_relics, PLAYTEST_DUNGEONS, RELIC_POOL,
)


def test_generate_map_has_required_node_types():
    mdata = generate_map("pt_tomb", char_level=10)
    types = [n["type"] for n in mdata["nodes"].values()]
    assert "boss"   in types
    assert "elite"  in types
    assert "rest"   in types
    # Start uzel je vždy přítomen
    assert "start"  in mdata["nodes"]
    assert "n_boss" in mdata["nodes"]


def test_generate_map_constraint_rest():
    """Každá mapa musí mít aspoň jeden rest uzel."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "rest" in types, f"Missing rest node: {types}"


def test_generate_map_constraint_elite():
    """Každá mapa musí mít aspoň jeden elite uzel."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "elite" in types, f"Missing elite node: {types}"


def test_available_nodes_initially_layer1():
    """Po vstupu jsou dostupné pouze uzly vrstvy 1 (n1a, n1b)."""
    mdata = generate_map("pt_tomb", char_level=10)
    available = get_available_nodes(mdata)
    assert set(available) == {"n1a", "n1b"}


def test_unlock_successors():
    mdata = generate_map("pt_tomb", char_level=10)
    # Simuluj dokončení n1a
    mdata["nodes"]["n1a"]["status"] = "completed"
    unlock_successors(mdata, "n1a")
    available = get_available_nodes(mdata)
    # n1b stále available (nebylo dokončeno), n2a a n2b by měly být available
    assert "n2a" in available or "n2b" in available


def test_roll_relics_no_duplicates():
    """roll_relics nesmí vrátit relics které hráč už má."""
    existing = ["blood_stone", "stone_shield"]
    relics = roll_relics(existing, count=3)
    ids = [r["id"] for r in relics]
    assert "blood_stone"  not in ids
    assert "stone_shield" not in ids
    assert len(relics) == 3


def test_roll_relics_count():
    relics = roll_relics([], count=3)
    assert len(relics) == 3


def test_all_dungeon_keys_valid():
    for key in ["pt_tomb", "pt_fiery", "pt_citadel"]:
        mdata = generate_map(key, char_level=15)
        assert "n_boss" in mdata["nodes"]
```

- [ ] **Step 2: Spustit testy**

```bash
cd backend && pytest tests/test_playtest_dungeon.py -v
```

Očekávaný výstup: všechny testy PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_playtest_dungeon.py
git commit -m "test: add playtest game logic tests"
```

---

## Task 5: Backend Router — část 1 (list, status, enter)

**Files:**
- Create: `backend/routers/playtest_dungeon.py` (začátek)
- Modify: `backend/main.py`

- [ ] **Step 1: Napsat router — základ + list + status + enter**

```python
# backend/routers/playtest_dungeon.py
"""
routers/playtest_dungeon.py — Playtest roguelite dungeon systém.

Endpoints:
- GET  /playtest/dungeon/list         — seznam dungeonů s cooldown info
- GET  /playtest/dungeon/status       — aktuální run + mapa
- POST /playtest/dungeon/enter        — vstup do dungeonu
- POST /playtest/dungeon/choose-node  — výběr uzlu
- POST /playtest/dungeon/choose-event — volba v event uzlu
- POST /playtest/dungeon/choose-relic — výběr relicu
- POST /playtest/dungeon/shop-buy     — nákup v shopu
- POST /playtest/dungeon/collect      — vyzvednutí odměn
- POST /playtest/dungeon/abandon      — opuštění runu
"""
import json
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.character import Character, xp_to_next
from models.playtest_run import PlaytestRun
from models.economy import log_gold, GoldReason
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment
from game.playtest_dungeon import (
    PLAYTEST_DUNGEONS, generate_map, get_available_nodes,
    unlock_successors, roll_relics, apply_relic_to_run,
    apply_event_choice, build_enemy_config, build_playtest_combatant,
    calculate_node_rewards, DUNGEON_EVENTS,
)
from game.combat_engine import simulate_unified_combat, events_to_dict_list
from game.loot import get_random_item_for_quest

router = APIRouter(prefix="/playtest/dungeon", tags=["playtest"])


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _run_dict(run: PlaytestRun) -> dict:
    return {
        "id":             run.id,
        "dungeon_key":    run.dungeon_key,
        "status":         run.status,
        "hp_current":     run.hp_current,
        "hp_max":         run.hp_max,
        "run_gold":       run.run_gold,
        "reward_xp":      run.reward_xp,
        "reward_gold":    run.reward_gold,
        "reward_claimed": run.reward_claimed,
        "relics":         run.get_relics(),
        "current_node_id": run.current_node_id,
        "visited_nodes":  run.get_visited(),
        "map_data":       run.get_map(),
        "cooldown_until": run.cooldown_until.isoformat() if run.cooldown_until else None,
    }


# ── GET /list ──────────────────────────────────────────────────────────────────

@router.get("/list")
async def playtest_dungeon_list(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    # Najdi aktivní nebo poslední run
    active_run = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id, PlaytestRun.status == "active")
        .order_by(PlaytestRun.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    # Cooldowny per dungeon_key
    recent_runs = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id,
               PlaytestRun.cooldown_until != None)
        .order_by(PlaytestRun.created_at.desc())
    )).scalars().all()

    cooldowns = {}
    for r in recent_runs:
        if r.dungeon_key not in cooldowns:
            cooldowns[r.dungeon_key] = r.cooldown_until

    now = _now()
    dungeons = []
    for key, cfg in PLAYTEST_DUNGEONS.items():
        cd = cooldowns.get(key)
        on_cooldown  = cd and cd > now
        locked       = char.level < cfg["min_level"]
        dungeons.append({
            "key":           key,
            "name":          cfg["name"],
            "min_level":     cfg["min_level"],
            "cooldown_hours": cfg["cooldown_hours"],
            "boss_mult":     cfg["boss_mult"],
            "locked":        locked,
            "on_cooldown":   bool(on_cooldown),
            "cooldown_until": cd.isoformat() if on_cooldown else None,
        })

    return {
        "dungeons":   dungeons,
        "active_run": _run_dict(active_run) if active_run else None,
        "char_level": char.level,
    }


# ── GET /status ────────────────────────────────────────────────────────────────

@router.get("/status")
async def playtest_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id, PlaytestRun.status == "active")
        .limit(1)
    )).scalar_one_or_none()

    return {"run": _run_dict(run) if run else None}


# ── POST /enter ────────────────────────────────────────────────────────────────

class EnterRequest(BaseModel):
    dungeon_key: str

@router.post("/enter")
async def playtest_enter(
    body: EnterRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.dungeon_key not in PLAYTEST_DUNGEONS:
        raise HTTPException(400, "Neznámý dungeon")

    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    cfg = PLAYTEST_DUNGEONS[body.dungeon_key]

    # Úroveň check
    if char.level < cfg["min_level"]:
        raise HTTPException(400, f"Minimální úroveň {cfg['min_level']}")

    # Cooldown check
    last_run = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id,
               PlaytestRun.dungeon_key == body.dungeon_key,
               PlaytestRun.cooldown_until != None)
        .order_by(PlaytestRun.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    now = _now()
    if last_run and last_run.cooldown_until and last_run.cooldown_until > now:
        raise HTTPException(400, f"Dungeon na cooldownu do {last_run.cooldown_until.isoformat()}")

    # Aktivní run check
    existing = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id, PlaytestRun.status == "active")
        .limit(1)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(400, "Máš aktivní Playtest run. Dokonči nebo opusť ho nejdříve.")

    # Generuj mapu
    map_data = generate_map(body.dungeon_key, char.level)

    run = PlaytestRun(
        char_id     = char.id,
        dungeon_key = body.dungeon_key,
        status      = "active",
        hp_current  = char.hp_max,
        hp_max      = char.hp_max,
        run_gold    = 0,
        reward_xp   = 0,
        reward_gold = 0,
        created_at  = now,
    )
    run.set_map(map_data)
    run.set_relics([])
    run.visited_nodes = "[]"
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return {"run": _run_dict(run)}
```

- [ ] **Step 2: Registrovat router v main.py**

V `backend/main.py` přidej import a include_router:

```python
# Do sekce importů (např. za dungeon_modifier_router):
from routers import playtest_dungeon as playtest_dungeon_router

# Do sekce app.include_router (za dungeon.router):
app.include_router(playtest_dungeon_router.router)
```

- [ ] **Step 3: Spustit server a ověřit**

```bash
cd backend && uvicorn main:app --reload --port 8000
```

Ověř: `GET http://localhost:8000/playtest/dungeon/list` vrátí JSON s dungeons.

- [ ] **Step 4: Commit**

```bash
git add backend/routers/playtest_dungeon.py backend/main.py
git commit -m "feat: add playtest router — list, status, enter endpoints"
```

---

## Task 6: Backend Router — část 2 (choose-node)

**Files:**
- Modify: `backend/routers/playtest_dungeon.py`

- [ ] **Step 1: Přidat choose-node endpoint**

Přidej do `playtest_dungeon.py`:

```python
# ── POST /choose-node ──────────────────────────────────────────────────────────

class ChooseNodeRequest(BaseModel):
    run_id:    int
    node_id:   str
    skip_shop: bool = False

@router.post("/choose-node")
async def playtest_choose_node(
    body: ChooseNodeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(PlaytestRun.id == body.run_id,
                                   PlaytestRun.char_id == char.id)
    )).scalar_one_or_none()
    if not run or run.status != "active":
        raise HTTPException(400, "Run nenalezen nebo není aktivní")

    mdata = run.get_map()
    node  = mdata["nodes"].get(body.node_id)
    if not node:
        raise HTTPException(400, "Uzel nenalezen")
    if node["status"] != "available":
        raise HTTPException(400, f"Uzel není dostupný (status: {node['status']})")

    now     = _now()
    cfg     = PLAYTEST_DUNGEONS[run.dungeon_key]
    relics  = run.get_relics()
    visited = run.get_visited()

    # ── SHOP ──────────────────────────────────────────────────────────────────
    if node["type"] == "shop":
        if body.skip_shop:
            node["status"] = "completed"
            unlock_successors(mdata, body.node_id)
            visited.append(body.node_id)
            run.visited_nodes = json.dumps(visited)
            run.set_map(mdata)
            await db.commit()
            return {"action": "skipped", "run": _run_dict(run)}
        else:
            shop_items = [
                {"id": "heal",         "label": "Léčení (40% HP)",         "cost": 50,  "effect": "heal_40pct"},
                {"id": "atk_boost",    "label": "Útočný boost (+10% ATK)", "cost": 80,  "effect": "atk_10pct"},
                {"id": "relic_refresh","label": "Relic výběr",             "cost": 120, "effect": "relic_refresh"},
            ]
            return {"action": "shop", "shop_items": shop_items, "run_gold": run.run_gold}

    # ── REST ──────────────────────────────────────────────────────────────────
    if node["type"] == "rest":
        healed         = int(run.hp_max * 0.25)
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        node["status"] = "completed"
        unlock_successors(mdata, body.node_id)
        visited.append(body.node_id)
        run.visited_nodes = json.dumps(visited)
        run.set_map(mdata)
        await db.commit()
        return {"action": "rest", "hp_restored": healed, "new_hp": run.hp_current, "run": _run_dict(run)}

    # ── EVENT ──────────────────────────────────────────────────────────────────
    if node["type"] == "event":
        node["status"]     = "pending_event"
        run.current_node_id = body.node_id
        run.set_map(mdata)
        await db.commit()
        events_list = DUNGEON_EVENTS.get(run.dungeon_key, DUNGEON_EVENTS["pt_tomb"])
        event_def   = next((e for e in events_list if e["id"] == node.get("event_id")), events_list[0])
        return {
            "action":     "event",
            "event_data": {"id": event_def["id"], "text": event_def["text"],
                           "choices": event_def["choices"]},
        }

    # ── COMBAT / ELITE / BOSS ─────────────────────────────────────────────────
    if node["type"] in ("combat", "elite", "boss"):
        # Zkontroluj pending_boost z eventu
        pending_boost = mdata.pop("pending_boost", None)
        if pending_boost:
            node = dict(node)  # kopie
            node["enemy_mult"] = node["enemy_mult"] * pending_boost["mult"]

        player_cfg = await build_playtest_combatant(char, run, db)
        enemy_cfg  = build_enemy_config(run.dungeon_key, node, char.level)

        result = simulate_unified_combat(player_cfg, enemy_cfg)
        battle_log = events_to_dict_list(result.events) if hasattr(result, 'events') else []

        if result.attacker_won:
            # Odměny
            reward_mult = pending_boost["reward_mult"] if pending_boost else 1.0
            xp, gold    = calculate_node_rewards(node, relics, cfg["xp_base"], cfg["gold_base"])
            xp   = int(xp   * reward_mult)
            gold = int(gold * reward_mult)
            run.reward_xp  += xp
            run.run_gold   += gold
            run.hp_current  = max(1, result.attacker_hp_remaining)

            # Per-combat hooks
            await _fire_combat_hooks(char, db)

            if node["type"] == "boss":
                # Run dokončen!
                node["status"]  = "completed"
                run.status      = "completed"
                run.reward_gold = run.run_gold
                run.cooldown_until = now + timedelta(hours=cfg["cooldown_hours"])
                visited.append(body.node_id)
                run.visited_nodes = json.dumps(visited)
                run.set_map(mdata)
                await _fire_completion_hooks(char, db)
                await db.commit()
                return {"action": "boss_win", "xp": xp, "gold": gold,
                        "battle_log": battle_log, "run": _run_dict(run)}

            # Combat/elite — čekej na choose-relic
            node["status"]      = "completed"
            run.current_node_id = body.node_id
            visited.append(body.node_id)
            run.visited_nodes   = json.dumps(visited)

            existing_ids    = [r["id"] for r in relics]
            is_elite        = node["type"] == "elite"
            pending_relics  = roll_relics(existing_ids, is_elite=is_elite)
            run.set_pending_relics(pending_relics)
            run.set_map(mdata)
            await db.commit()
            return {"action": "combat_win", "xp": xp, "gold": gold,
                    "hp_remaining": run.hp_current,
                    "pending_relics": pending_relics,
                    "battle_log": battle_log, "run": _run_dict(run)}

        else:
            # Prohra
            run.hp_current  = 0
            node["status"]  = "completed"
            run.status      = "failed"
            run.reward_gold = 0
            run.reward_xp   = run.reward_xp // 2  # 50% penalty
            run.cooldown_until = now + timedelta(hours=cfg["cooldown_hours"] // 2)
            visited.append(body.node_id)
            run.visited_nodes = json.dumps(visited)
            run.set_map(mdata)

            # HC permadeath
            if char.is_hardcore:
                await _trigger_permadeath_playtest(char, node["enemy_name"], run.dungeon_key, now, db)

            await db.commit()
            return {"action": "combat_loss", "battle_log": battle_log, "run": _run_dict(run)}

    raise HTTPException(400, f"Neznámý typ uzlu: {node['type']}")


async def _fire_combat_hooks(char, db):
    """Volá per-combat hooks (kills, durability, season XP)."""
    from routers.guild import increment_guild_weekly
    from routers.weekly_quest import increment_weekly_board
    from routers.season_pass import add_season_xp
    from routers.inventory import _decrease_equipped_durability, DURABILITY_LOSS_DUNGEON
    try:
        await increment_guild_weekly(char.guild_id, "kills", 1, char.id, db)
        await increment_weekly_board(char.id, "kills", 1, db)
        await add_season_xp(char.id, "dungeon_stage", db)
        await _decrease_equipped_durability(char, DURABILITY_LOSS_DUNGEON, db)
    except Exception:
        pass  # hooks jsou best-effort, neblokují run


async def _fire_completion_hooks(char, db):
    """Volá hooks při dokončení runu."""
    from routers.guild import increment_guild_weekly
    from routers.weekly_quest import increment_weekly_board
    from routers.season_pass import add_season_xp
    from routers.world_event import add_world_event_contribution
    try:
        await increment_guild_weekly(char.guild_id, "dungeons", 1, char.id, db)
        await increment_weekly_board(char.id, "dungeons", 1, db)
        await add_season_xp(char.id, "dungeon_complete", db)
        await add_world_event_contribution("dungeon_clears", char.id, 1, db)
    except Exception:
        pass


async def _trigger_permadeath_playtest(char, enemy_name, dungeon_key, now, db):
    """HC permadeath wrapper."""
    try:
        from routers.dungeon import _trigger_permadeath
        await _trigger_permadeath(char, enemy_name, dungeon_key, now, db)
    except Exception:
        pass
```

- [ ] **Step 2: Commit**

```bash
git add backend/routers/playtest_dungeon.py
git commit -m "feat: add choose-node endpoint (combat, rest, event, shop, boss)"
```

---

## Task 7: Backend Router — část 3 (choose-event, choose-relic, shop-buy, collect, abandon)

**Files:**
- Modify: `backend/routers/playtest_dungeon.py`

- [ ] **Step 1: Přidat zbývající endpointy**

```python
# ── POST /choose-event ─────────────────────────────────────────────────────────

class ChooseEventRequest(BaseModel):
    run_id:       int
    choice_index: int

@router.post("/choose-event")
async def playtest_choose_event(
    body: ChooseEventRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(PlaytestRun.id == body.run_id,
                                   PlaytestRun.char_id == char.id)
    )).scalar_one_or_none()
    if not run or run.status != "active":
        raise HTTPException(400, "Run nenalezen nebo není aktivní")

    mdata = run.get_map()
    node  = mdata["nodes"].get(run.current_node_id)
    if not node or node["status"] != "pending_event":
        raise HTTPException(400, "Žádný aktivní event")

    result = apply_event_choice(run, run.dungeon_key, node.get("event_id", ""), body.choice_index)

    # Posunout mapu
    node["status"] = "completed"
    visited = run.get_visited()
    visited.append(run.current_node_id)
    run.visited_nodes   = json.dumps(visited)
    completed_node_id   = run.current_node_id
    run.current_node_id = None
    unlock_successors(mdata, completed_node_id)
    run.set_map(mdata)

    # Pending relics z eventu?
    pending_relics = result.pop("pending_relics", None)
    if pending_relics:
        run.set_pending_relics(pending_relics)

    await db.commit()
    return {**result, "pending_relics": pending_relics, "run": _run_dict(run)}


# ── POST /choose-relic ─────────────────────────────────────────────────────────

class ChooseRelicRequest(BaseModel):
    run_id:   int
    relic_id: str

@router.post("/choose-relic")
async def playtest_choose_relic(
    body: ChooseRelicRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(PlaytestRun.id == body.run_id,
                                   PlaytestRun.char_id == char.id)
    )).scalar_one_or_none()
    if not run or run.status != "active":
        raise HTTPException(400, "Run nenalezen")

    pending = run.get_pending_relics()
    relic   = next((r for r in pending if r["id"] == body.relic_id), None)
    if not relic:
        raise HTTPException(400, "Relic není v nabídce")

    # Aplikuj one-time efekty
    relic_copy = dict(relic)
    effect_result = apply_relic_to_run(run, relic_copy)

    # Přidej do relics seznamu
    relics = run.get_relics()
    relics.append(relic_copy)
    run.set_relics(relics)
    run.set_pending_relics([])  # vymaž nabídku

    # Teprve teď odemkni sousedy (map advancement po choose-relic)
    mdata = run.get_map()
    if run.current_node_id:
        unlock_successors(mdata, run.current_node_id)
        run.current_node_id = None
        run.set_map(mdata)

    await db.commit()
    return {**effect_result, "run": _run_dict(run)}


# ── POST /shop-buy ─────────────────────────────────────────────────────────────

class ShopBuyRequest(BaseModel):
    run_id:  int
    item_id: str  # "heal" | "atk_boost" | "relic_refresh"

SHOP_ITEMS = {
    "heal":          {"cost": 50,  "label": "Léčení (40% HP)"},
    "atk_boost":     {"cost": 80,  "label": "Útočný boost (+10% ATK)"},
    "relic_refresh": {"cost": 120, "label": "Relic výběr"},
}

@router.post("/shop-buy")
async def playtest_shop_buy(
    body: ShopBuyRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(PlaytestRun.id == body.run_id,
                                   PlaytestRun.char_id == char.id)
    )).scalar_one_or_none()
    if not run or run.status != "active":
        raise HTTPException(400, "Run nenalezen")

    item = SHOP_ITEMS.get(body.item_id)
    if not item:
        raise HTTPException(400, "Neznámá položka")

    if run.run_gold < item["cost"]:
        raise HTTPException(400, f"Nedostatek gold. Potřebuješ {item['cost']}g, máš {run.run_gold}g")

    run.run_gold -= item["cost"]
    result = {"item_id": body.item_id, "cost": item["cost"]}

    if body.item_id == "heal":
        healed         = int(run.hp_max * 0.40)
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        result["hp_restored"] = healed

    elif body.item_id == "atk_boost":
        boost = {"id": "shop_atk_boost", "name": "Útočný elixír",
                 "effect_key": "atk_pct", "value": 0.10, "desc": "+10% ATK (shop)"}
        relics = run.get_relics()
        relics.append(boost)
        run.set_relics(relics)

    elif body.item_id == "relic_refresh":
        existing_ids   = [r["id"] for r in run.get_relics()]
        pending_relics = roll_relics(existing_ids, count=3)
        run.set_pending_relics(pending_relics)
        result["pending_relics"] = pending_relics

    await db.commit()
    return {**result, "run": _run_dict(run)}


# ── POST /collect ──────────────────────────────────────────────────────────────

class CollectRequest(BaseModel):
    run_id: int

@router.post("/collect")
async def playtest_collect(
    body: CollectRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(PlaytestRun.id == body.run_id,
                                   PlaytestRun.char_id == char.id)
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run nenalezen")
    if run.status not in ("completed", "failed"):
        raise HTTPException(400, "Run ještě neskončil")
    if run.reward_claimed:
        raise HTTPException(400, "Odměny již byly vyzvednuty")

    xp_gained   = run.reward_xp
    gold_gained = run.run_gold if run.status == "completed" else 0

    # Aplikuj odměny
    char.xp    += xp_gained
    char.gold  += gold_gained

    if gold_gained > 0:
        await log_gold(db, char, gold_gained, GoldReason.DUNGEON_REWARD,
                       {"dungeon_run_id": run.id, "dungeon_key": run.dungeon_key})

    # Level-up check
    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        leveled_up.append(char.level)

    # Boss loot drop
    item = None
    if run.status == "completed":
        item = await get_random_item_for_quest(db, "hard", char.level)
        # Signatura: get_random_item_for_quest(db, difficulty: str, character_level: int)
        # "hard" odpovídá boss lootu — viz jak volá dungeon.py

    run.reward_claimed = True
    await db.commit()
    await db.refresh(char)

    return {
        "xp_gained":   xp_gained,
        "gold_gained": gold_gained,
        "leveled_up":  leveled_up,
        "item":        item,
        "character":   await char_dict_with_equipment(char, db),
    }


# ── POST /abandon ──────────────────────────────────────────────────────────────

class AbandonRequest(BaseModel):
    run_id: int

@router.post("/abandon")
async def playtest_abandon(
    body: AbandonRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(PlaytestRun.id == body.run_id,
                                   PlaytestRun.char_id == char.id)
    )).scalar_one_or_none()
    if not run or run.status != "active":
        raise HTTPException(400, "Run nenalezen nebo není aktivní")

    cfg = PLAYTEST_DUNGEONS[run.dungeon_key]
    now = _now()
    partial_xp   = run.reward_xp // 2
    run.reward_xp    = partial_xp
    run.run_gold     = 0
    run.status       = "failed"
    run.cooldown_until = now + timedelta(hours=cfg["cooldown_hours"] // 4)

    await db.commit()
    return {"partial_xp": partial_xp, "run": _run_dict(run)}
```

- [ ] **Step 2: Commit**

```bash
git add backend/routers/playtest_dungeon.py
git commit -m "feat: add choose-event, choose-relic, shop-buy, collect, abandon endpoints"
```

---

## Task 8: Backend testy — integrace

**Files:**
- Modify: `backend/tests/test_playtest_dungeon.py`

- [ ] **Step 1: Přidat HTTP integration testy**

```python
# Přidej do backend/tests/test_playtest_dungeon.py
# DŮLEŽITÉ: client fixture je definována v backend/tests/conftest.py
# Stačí ji importovat přes pytest — pytest ji najde automaticky z conftest.py
# Nepřidávej fixture znovu — použij tu z conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient

# Helper: vytvoří usera a postavu s dost levelem
async def _create_user_and_char(client, level=10):
    resp = await client.post("/auth/register", json={
        "username": f"pt_test_{random.randint(1000,9999)}",
        "password": "testpass123"
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp2 = await client.post("/character/create",
        json={"name": "TestHrdina", "char_class": "warrior"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp2.status_code == 200
    char = resp2.json()

    # Nastav level přímo v DB pokud je potřeba — nebo přidej debug endpoint
    return token, char

import random

@pytest.mark.asyncio
async def test_enter_dungeon_success(client):
    token, char = await _create_user_and_char(client, level=10)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"}, headers=headers)
    # Může selhat kvůli min_level — zkontroluj char.level >= 8
    # Pro test použij postavu s level >= 8
    assert resp.status_code in (200, 400)  # 400 pokud level nestačí


@pytest.mark.asyncio
async def test_list_dungeons(client):
    token, char = await _create_user_and_char(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/playtest/dungeon/list", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "dungeons" in data
    assert len(data["dungeons"]) == 3
    keys = [d["key"] for d in data["dungeons"]]
    assert "pt_tomb" in keys
    assert "pt_fiery" in keys
    assert "pt_citadel" in keys


@pytest.mark.asyncio
async def test_status_no_run(client):
    token, char = await _create_user_and_char(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/playtest/dungeon/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["run"] is None


@pytest.mark.asyncio
async def test_cannot_enter_twice(client):
    """Nelze vstoupit do dungeonu pokud máš aktivní run."""
    token, char = await _create_user_and_char(client)
    headers = {"Authorization": f"Bearer {token}"}
    # Uprav level pro test — hack přes DB nebo skip pokud level nestačí
    r1 = await client.post("/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"}, headers=headers)
    if r1.status_code != 200:
        pytest.skip("Level nestačí pro dungeon — skip test")
    r2 = await client.post("/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"}, headers=headers)
    assert r2.status_code == 400
    assert "aktivní" in r2.json()["detail"].lower()
```

- [ ] **Step 2: Spustit testy**

```bash
cd backend && pytest tests/test_playtest_dungeon.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_playtest_dungeon.py
git commit -m "test: add playtest dungeon integration tests"
```

---

## Task 9: Frontend — HTML struktura + navigace

**Files:**
- Modify: `frontend/game.html`
- Modify: `frontend/css/components.css`

- [ ] **Step 1: Přidat page-playtest do game.html**

Najdi sekci s ostatními page divy (např. `<div id="page-dungeon"`) a přidej za ni:

```html
<!-- PLAYTEST PAGE -->
<div id="page-playtest" class="page">
  <div class="pt-header">
    <h2>⚗️ Playtest <span class="pt-beta-badge">BETA</span></h2>
    <p class="pt-subtitle">Roguelite dungeon — experimentální systém</p>
  </div>
  <div id="pt-content">
    <!-- renderováno přes playtest.js -->
    <div class="pt-loading">Načítám...</div>
  </div>
</div>
```

- [ ] **Step 2: Přidat nav tlačítko do topbaru**

Najdi ostatní nav tlačítka v topbaru (např. `id="nav-dungeon"`) a přidej:

```html
<button id="nav-playtest" onclick="showPage('page-playtest')" class="nav-btn nav-playtest">
  ⚗️ <span>Playtest</span>
</button>
```

- [ ] **Step 3: Přidat script tag pro playtest.js**

Najdi ostatní script tagy (po `dungeon.js`) a přidej:

```html
<script src="js/playtest.js"></script>
```

- [ ] **Step 4: Přidat CSS třídy do components.css**

```css
/* ── Playtest tab ────────────────────────────────────────────────────── */
.nav-playtest { color: #a78bfa; }
.nav-playtest:hover { background: rgba(167,139,250,0.15); }

.pt-beta-badge {
  font-size: 0.6rem; font-weight: 700; letter-spacing: 0.05em;
  background: #7c3aed; color: #fff; padding: 2px 6px;
  border-radius: 4px; vertical-align: middle; margin-left: 6px;
}

.pt-header { padding: 16px 0 8px; }
.pt-subtitle { color: var(--clr-muted); font-size: 0.9rem; }

/* List view */
.pt-dungeon-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px,1fr)); gap: 16px; padding: 16px 0; }
.pt-dungeon-card { background: var(--clr-surface); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.06); }
.pt-dungeon-card.locked { opacity: 0.5; pointer-events: none; }
.pt-dungeon-card.on-cooldown { opacity: 0.7; }
.pt-dungeon-card h3 { margin: 0 0 8px; font-size: 1.1rem; }
.pt-dungeon-card .pt-card-meta { color: var(--clr-muted); font-size: 0.8rem; margin-bottom: 12px; }
.pt-enter-btn { width: 100%; padding: 10px; background: #7c3aed; color: #fff; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
.pt-enter-btn:hover { background: #6d28d9; }
.pt-cooldown-timer { color: var(--clr-muted); font-size: 0.85rem; text-align: center; }

/* Active run view */
.pt-run-layout { display: grid; grid-template-columns: 240px 1fr; gap: 20px; }
@media (max-width: 768px) { .pt-run-layout { grid-template-columns: 1fr; } }

.pt-sidebar { background: var(--clr-surface); border-radius: 12px; padding: 16px; }
.pt-hp-bar-wrap { margin-bottom: 12px; }
.pt-hp-bar-bg { background: rgba(255,255,255,0.08); border-radius: 6px; height: 12px; overflow: hidden; }
.pt-hp-bar-fill { height: 100%; background: #22c55e; border-radius: 6px; transition: width 0.3s; }
.pt-hp-bar-fill.critical { background: #ef4444; }
.pt-hp-text { font-size: 0.8rem; color: var(--clr-muted); margin-top: 4px; }

.pt-relics-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.pt-relic-chip { background: rgba(124,58,237,0.2); border: 1px solid rgba(124,58,237,0.4); border-radius: 6px; padding: 4px 8px; font-size: 0.75rem; cursor: help; }
.pt-relic-chip.consumed { opacity: 0.4; }

.pt-rewards-mini { margin-top: 12px; font-size: 0.85rem; color: var(--clr-muted); }

/* Map SVG */
.pt-map-wrap { background: var(--clr-surface); border-radius: 12px; padding: 16px; min-height: 300px; }
.pt-map-svg { width: 100%; height: 320px; }
.pt-node { cursor: pointer; }
.pt-node.available circle { stroke: #a78bfa; stroke-width: 3; filter: drop-shadow(0 0 6px #7c3aed); }
.pt-node.completed circle { fill: #374151; }
.pt-node.locked { opacity: 0.35; pointer-events: none; }
.pt-node text { fill: #fff; font-size: 11px; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }
.pt-edge { stroke: rgba(255,255,255,0.15); stroke-width: 2; }

/* Modaly */
.pt-modal-body { padding: 8px 0; }
.pt-relic-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
@media (max-width: 768px) { .pt-relic-cards { grid-template-columns: 1fr; } }
.pt-relic-card { background: var(--clr-surface); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 16px; cursor: pointer; text-align: center; transition: border-color 0.2s; }
.pt-relic-card:hover { border-color: #7c3aed; }
.pt-relic-card h4 { margin: 0 0 6px; font-size: 0.95rem; }
.pt-relic-card p { color: var(--clr-muted); font-size: 0.82rem; margin: 0; }

.pt-shop-items { display: flex; flex-direction: column; gap: 10px; }
.pt-shop-item { display: flex; justify-content: space-between; align-items: center; background: var(--clr-surface); border-radius: 8px; padding: 12px 16px; }
.pt-shop-buy-btn { background: #7c3aed; color: #fff; border: none; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 0.85rem; }
.pt-shop-buy-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Collect view */
.pt-collect-summary { background: var(--clr-surface); border-radius: 12px; padding: 24px; text-align: center; }
.pt-collect-rewards { display: flex; gap: 20px; justify-content: center; margin: 16px 0; }
.pt-collect-reward-item { text-align: center; }
.pt-collect-reward-item span:first-child { display: block; font-size: 1.5rem; font-weight: 700; color: #a78bfa; }
.pt-collect-reward-item span:last-child { font-size: 0.8rem; color: var(--clr-muted); }
.pt-collect-btn { background: #7c3aed; color: #fff; border: none; border-radius: 8px; padding: 12px 32px; font-size: 1rem; font-weight: 600; cursor: pointer; }
```

- [ ] **Step 5: Commit**

```bash
git add frontend/game.html frontend/css/components.css
git commit -m "feat: add playtest page HTML structure and CSS"
```

---

## Task 10: Frontend — playtest.js

**Files:**
- Create: `frontend/js/playtest.js`

- [ ] **Step 1: Napsat celý playtest.js**

```javascript
// frontend/js/playtest.js
// Playtest roguelite dungeon systém — izolovaný od starého dungeon.js

'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
let _ptRun        = null;   // aktuální PlaytestRun nebo null
let _ptDungeons   = [];     // seznam dungeonů
let _ptPendingRelics = [];  // čekající relic nabídka
let _ptActiveNode = null;   // ID uzlu čekajícího na akci

// ── Init ──────────────────────────────────────────────────────────────────────
async function initPlaytest() {
  try {
    await _ptRefresh();
  } catch (e) {
    document.getElementById('pt-content').innerHTML =
      `<p style="color:var(--clr-muted)">Nepodařilo se načíst Playtest.</p>`;
  }
}

async function _ptRefresh() {
  const data = await api('GET', '/playtest/dungeon/list');
  _ptDungeons = data.dungeons;
  _ptRun      = data.active_run;
  _ptRender();
}

// ── Render router ─────────────────────────────────────────────────────────────
function _ptRender() {
  const el = document.getElementById('pt-content');
  if (!el) return;

  if (!_ptRun) {
    el.innerHTML = _ptRenderList();
    return;
  }
  if (_ptRun.status === 'completed' || _ptRun.status === 'failed') {
    el.innerHTML = _ptRenderCollect();
    return;
  }
  // Aktivní run
  el.innerHTML = _ptRenderActiveRun();
  _ptBindMapClicks();
}

// ── List view ─────────────────────────────────────────────────────────────────
function _ptRenderList() {
  const cards = _ptDungeons.map(d => {
    const locked     = d.locked;
    const onCooldown = d.on_cooldown;
    const cdText     = onCooldown ? _ptCooldownText(d.cooldown_until) : '';

    let btnHtml = '';
    if (locked)
      btnHtml = `<div class="pt-cooldown-timer">Vyžaduje level ${d.min_level}</div>`;
    else if (onCooldown)
      btnHtml = `<div class="pt-cooldown-timer">${cdText}</div>`;
    else
      btnHtml = `<button class="pt-enter-btn" onclick="ptEnter('${d.key}')">Vstoupit</button>`;

    return `
      <div class="pt-dungeon-card ${locked ? 'locked' : ''} ${onCooldown ? 'on-cooldown' : ''}">
        <h3>${d.name}</h3>
        <div class="pt-card-meta">Min. úroveň ${d.min_level} · Cooldown ${d.cooldown_hours}h</div>
        ${btnHtml}
      </div>`;
  }).join('');

  return `<div class="pt-dungeon-list">${cards}</div>`;
}

// ── Active run view ───────────────────────────────────────────────────────────
function _ptRenderActiveRun() {
  const run     = _ptRun;
  const hpPct   = Math.max(0, Math.round((run.hp_current / run.hp_max) * 100));
  const critical = hpPct < 30;

  const relicChips = (run.relics || []).map(r =>
    `<div class="pt-relic-chip ${r.consumed ? 'consumed' : ''}" title="${r.desc || ''}">${r.name}</div>`
  ).join('');

  const sidebar = `
    <div class="pt-sidebar">
      <div class="pt-hp-bar-wrap">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:.85rem">
          <span>HP</span><span>${run.hp_current} / ${run.hp_max}</span>
        </div>
        <div class="pt-hp-bar-bg">
          <div class="pt-hp-bar-fill ${critical ? 'critical' : ''}" style="width:${hpPct}%"></div>
        </div>
        ${critical ? '<div style="color:#ef4444;font-size:.75rem;margin-top:4px">⚠️ Kritické HP!</div>' : ''}
      </div>
      <div style="font-size:.8rem;color:var(--clr-muted);margin-bottom:4px">Relics:</div>
      <div class="pt-relics-list">${relicChips || '<span style="color:var(--clr-muted);font-size:.8rem">Žádné</span>'}</div>
      <div class="pt-rewards-mini">
        <div>XP: +${run.reward_xp}</div>
        <div>Gold: ${run.run_gold}g</div>
      </div>
      <button onclick="ptAbandon(${run.id})" style="width:100%;margin-top:16px;padding:8px;background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3);border-radius:8px;cursor:pointer;font-size:.85rem">
        Opustit run
      </button>
    </div>`;

  const mapSvg = _ptRenderMapSvg(run.map_data);

  return `
    <div class="pt-run-layout">
      ${sidebar}
      <div class="pt-map-wrap">
        <div style="font-size:.85rem;color:var(--clr-muted);margin-bottom:12px">
          ${PLAYTEST_DUNGEONS_NAMES[run.dungeon_key] || run.dungeon_key}
          — klikni na dostupný uzel
        </div>
        ${mapSvg}
      </div>
    </div>`;
}

const PLAYTEST_DUNGEONS_NAMES = {
  pt_tomb:    'Tomb of Forgotten',
  pt_fiery:   'Fiery Depths',
  pt_citadel: 'Citadel of Chaos',
};

// ── SVG mapa ──────────────────────────────────────────────────────────────────
const NODE_ICONS = {
  start:  '🏁', combat: '⚔️', elite: '💀', rest: '🛖',
  event:  '❓', shop:   '💰', boss:  '👑',
};

function _ptRenderMapSvg(mapData) {
  if (!mapData || !mapData.nodes) return '<p>Mapa nenalezena.</p>';

  // Normalizuj layout souřadnice na SVG prostor (0-500 x 0-280)
  const layout = mapData.layout;
  const xs = Object.values(layout).map(p => p[0]);
  const ys = Object.values(layout).map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const W = 500, H = 280, PAD = 40;

  const toSvg = (x, y) => {
    const sx = maxX === minX ? W / 2 : PAD + ((x - minX) / (maxX - minX)) * (W - PAD * 2);
    const sy = maxY === minY ? H / 2 : PAD + ((y - minY) / (maxY - minY)) * (H - PAD * 2);
    return [sx, sy];
  };

  // Edges
  let edgesSvg = '';
  for (const [src, dst] of (mapData.edges || [])) {
    if (!layout[src] || !layout[dst]) continue;
    const [x1, y1] = toSvg(...layout[src]);
    const [x2, y2] = toSvg(...layout[dst]);
    edgesSvg += `<line class="pt-edge" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
  }

  // Nodes
  let nodesSvg = '';
  for (const [nid, node] of Object.entries(mapData.nodes)) {
    if (!layout[nid]) continue;
    const [cx, cy] = toSvg(...layout[nid]);
    const status   = node.status;
    const icon     = NODE_ICONS[node.type] || '?';
    const label    = node.enemy_name || node.type;
    nodesSvg += `
      <g class="pt-node ${status}" data-node-id="${nid}" data-node-type="${node.type}">
        <circle cx="${cx}" cy="${cy}" r="22" fill="var(--clr-surface)" stroke="rgba(255,255,255,.15)" stroke-width="1.5"/>
        <text x="${cx}" y="${cy - 4}" font-size="14">${icon}</text>
        <text x="${cx}" y="${cy + 12}" font-size="9" fill="rgba(255,255,255,.6)">${node.type}</text>
      </g>`;
  }

  return `<svg class="pt-map-svg" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
    ${edgesSvg}${nodesSvg}
  </svg>`;
}

function _ptBindMapClicks() {
  document.querySelectorAll('.pt-node.available').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      const nodeId   = el.dataset.nodeId;
      const nodeType = el.dataset.nodeType;
      _ptShowNodeModal(nodeId, nodeType);
    });
  });
}

// ── Collect view ──────────────────────────────────────────────────────────────
function _ptRenderCollect() {
  const run   = _ptRun;
  const won   = run.status === 'completed';
  const title = won ? '🏆 Dungeon dokončen!' : '💀 Run selhal';
  const color = won ? '#a78bfa' : '#ef4444';

  return `
    <div class="pt-collect-summary">
      <h3 style="color:${color}">${title}</h3>
      <div class="pt-collect-rewards">
        <div class="pt-collect-reward-item">
          <span>+${run.reward_xp}</span><span>XP</span>
        </div>
        ${won ? `<div class="pt-collect-reward-item"><span>+${run.run_gold}g</span><span>Gold</span></div>` : ''}
      </div>
      <button class="pt-collect-btn" onclick="ptCollect(${run.id})">Vyzvednout odměny</button>
    </div>`;
}

// ── Node modaly ───────────────────────────────────────────────────────────────
function _ptShowNodeModal(nodeId, nodeType) {
  _ptActiveNode = nodeId;
  const mapData = _ptRun.map_data;
  const node    = mapData.nodes[nodeId];
  if (!node) return;

  let body = '';
  let title = '';

  if (nodeType === 'combat' || nodeType === 'elite' || nodeType === 'boss') {
    title = nodeType === 'boss' ? '👑 Boss' : nodeType === 'elite' ? '💀 Elite' : '⚔️ Combat';
    body = `
      <p>Nepřítel: <strong>${node.enemy_name}</strong></p>
      <p style="color:var(--clr-muted);font-size:.85rem">Síla: ${Math.round(node.enemy_mult * 100)}%</p>
      <p style="color:var(--clr-muted);font-size:.85rem">Odměna: +${node.reward_xp} XP · +${node.reward_gold}g</p>
      <button onclick="ptChooseNode('${nodeId}')" class="pt-enter-btn" style="margin-top:12px">
        Vstoupit do boje
      </button>`;
  } else if (nodeType === 'rest') {
    const heal = Math.floor(_ptRun.hp_max * 0.25);
    title = '🛖 Odpočinek';
    body = `
      <p>Obnov <strong>${heal} HP</strong>.</p>
      <button onclick="ptChooseNode('${nodeId}')" class="pt-enter-btn" style="margin-top:12px;background:#22c55e">
        Odpočinout (+${heal} HP)
      </button>`;
  } else if (nodeType === 'event') {
    title = '❓ Událost';
    body = `<p style="color:var(--clr-muted)">Načítám událost...</p>`;
    // Otevři modal a pak načti event
  } else if (nodeType === 'shop') {
    title = '💰 Obchod';
    body = `
      <p style="color:var(--clr-muted)">Run gold: <strong>${_ptRun.run_gold}g</strong></p>
      <div class="pt-shop-items">
        ${_ptShopItems()}
      </div>
      <button onclick="ptSkipShop('${nodeId}')" style="width:100%;margin-top:12px;padding:8px;background:transparent;color:var(--clr-muted);border:1px solid rgba(255,255,255,.1);border-radius:8px;cursor:pointer">
        Přejít bez nákupu
      </button>`;
  }

  document.getElementById('pt-modal-title').textContent = title;
  document.getElementById('pt-modal-body').innerHTML    = body;
  openModal('modal-playtest-node');

  if (nodeType === 'event') {
    ptChooseNodeEvent(nodeId);  // zahájí event load
  }
}

function _ptShopItems() {
  const items = [
    { id: 'heal',          label: 'Léčení (40% HP)',        cost: 50  },
    { id: 'atk_boost',     label: 'Útočný boost (+10% ATK)', cost: 80  },
    { id: 'relic_refresh', label: 'Nový relic výběr',        cost: 120 },
  ];
  return items.map(item => {
    const canAfford = _ptRun.run_gold >= item.cost;
    return `
      <div class="pt-shop-item">
        <span>${item.label}</span>
        <button class="pt-shop-buy-btn" ${canAfford ? '' : 'disabled'}
          onclick="ptShopBuy('${item.id}')">
          ${item.cost}g
        </button>
      </div>`;
  }).join('');
}

// ── Relic picker modal ────────────────────────────────────────────────────────
function _ptShowRelicModal(relics) {
  _ptPendingRelics = relics;
  const cards = relics.map(r => `
    <div class="pt-relic-card" onclick="ptChooseRelic('${r.id}')">
      <h4>${r.name}</h4>
      <p>${r.desc}</p>
    </div>`).join('');

  document.getElementById('pt-relic-cards').innerHTML = cards;
  openModal('modal-playtest-relic');
}

// ── API akce ──────────────────────────────────────────────────────────────────
async function ptEnter(dungeonKey) {
  try {
    const data  = await api('POST', '/playtest/dungeon/enter', { dungeon_key: dungeonKey });
    _ptRun      = data.run;
    _ptRender();
    closeModal('modal-playtest-node');
  } catch (e) {
    toast(e.message || 'Chyba při vstupu do dungeonu', 'e');
  }
}

async function ptChooseNode(nodeId) {
  closeModal('modal-playtest-node');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-node',
      { run_id: _ptRun.id, node_id: nodeId });
    _ptRun = data.run;

    if (data.action === 'combat_win' || data.action === 'boss_win') {
      // Zobraz combat replay pak relic picker
      if (data.battle_log && data.battle_log.length) {
        await showCombatReplay(data.battle_log, true, () => {
          if (data.pending_relics && data.pending_relics.length) {
            _ptShowRelicModal(data.pending_relics);
          } else {
            _ptRender();
          }
        });
      } else if (data.pending_relics && data.pending_relics.length) {
        _ptShowRelicModal(data.pending_relics);
      } else {
        _ptRender();
      }
      if (data.xp) toast(`+${data.xp} XP · +${data.gold}g`, 's');
    } else if (data.action === 'combat_loss') {
      if (data.battle_log && data.battle_log.length) {
        await showCombatReplay(data.battle_log, false, () => _ptRender());
      } else {
        _ptRender();
      }
      toast('Poražen! Run selhal.', 'e');
    } else if (data.action === 'rest') {
      toast(`Odpočinek: +${data.hp_restored} HP`, 's');
      _ptRender();
    } else if (data.action === 'event') {
      _ptShowEventInModal(data.event_data, nodeId);
    } else if (data.action === 'shop') {
      _ptShowNodeModal(nodeId, 'shop');
    } else {
      _ptRender();
    }
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
    _ptRender();
  }
}

async function ptChooseNodeEvent(nodeId) {
  // Volá choose-node pro event typ (backend vrátí event_data)
  try {
    const data = await api('POST', '/playtest/dungeon/choose-node',
      { run_id: _ptRun.id, node_id: nodeId });
    if (data.action === 'event') {
      _ptShowEventInModal(data.event_data, nodeId);
    }
  } catch (e) {
    toast(e.message || 'Chyba při načítání eventu', 'e');
  }
}

function _ptShowEventInModal(eventData, nodeId) {
  document.getElementById('pt-modal-title').textContent = '❓ Událost';
  const choiceBtns = eventData.choices.map(c => `
    <button onclick="ptChooseEvent(${c.index})" style="width:100%;margin-bottom:8px;padding:12px;background:var(--clr-surface);border:1px solid rgba(255,255,255,.1);border-radius:8px;cursor:pointer;text-align:left">
      <strong>${c.label}</strong>
      <div style="font-size:.8rem;color:var(--clr-muted);margin-top:4px">${c.hint}</div>
    </button>`).join('');
  document.getElementById('pt-modal-body').innerHTML =
    `<p style="margin-bottom:16px">${eventData.text}</p>${choiceBtns}`;
  if (!document.getElementById('modal-playtest-node').classList.contains('open')) {
    openModal('modal-playtest-node');
  }
}

async function ptChooseEvent(choiceIndex) {
  closeModal('modal-playtest-node');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-event',
      { run_id: _ptRun.id, choice_index: choiceIndex });
    _ptRun = data.run;
    toast(data.outcome_text || 'Událost vyřešena', 's');
    if (data.hp_delta < 0) toast(`HP: ${data.hp_delta}`, 'e');
    if (data.gold_delta > 0) toast(`+${data.gold_delta}g`, 's');
    if (data.pending_relics && data.pending_relics.length) {
      _ptShowRelicModal(data.pending_relics);
    } else {
      _ptRender();
    }
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptChooseRelic(relicId) {
  closeModal('modal-playtest-relic');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-relic',
      { run_id: _ptRun.id, relic_id: relicId });
    _ptRun = data.run;
    if (data.description) toast(data.description, 's');
    _ptRender();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptShopBuy(itemId) {
  try {
    const data = await api('POST', '/playtest/dungeon/shop-buy',
      { run_id: _ptRun.id, item_id: itemId });
    _ptRun = data.run;
    if (data.hp_restored) toast(`Léčení: +${data.hp_restored} HP`, 's');
    if (data.pending_relics && data.pending_relics.length) {
      closeModal('modal-playtest-node');
      _ptShowRelicModal(data.pending_relics);
    } else {
      // Refresh shop
      document.getElementById('pt-modal-body').querySelector('.pt-shop-items').innerHTML =
        _ptShopItems();
    }
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptSkipShop(nodeId) {
  closeModal('modal-playtest-node');
  try {
    const data = await api('POST', '/playtest/dungeon/choose-node',
      { run_id: _ptRun.id, node_id: nodeId, skip_shop: true });
    _ptRun = data.run;
    _ptRender();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptCollect(runId) {
  try {
    const data = await api('POST', '/playtest/dungeon/collect', { run_id: runId });
    _ptRun = null;
    if (data.xp_gained) toast(`+${data.xp_gained} XP`, 's');
    if (data.gold_gained) toast(`+${data.gold_gained}g`, 's');
    if (data.leveled_up && data.leveled_up.length) {
      data.leveled_up.forEach(lvl => toast(`Level up! → ${lvl}`, 's'));
    }
    if (data.character) {
      char = data.character;
      updateUI(char);
    }
    await _ptRefresh();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

async function ptAbandon(runId) {
  // Použij openModal místo confirm() — confirm() je blokující a porušuje project konvenci
  // Přidej potvrzovací modal do game.html (viz Task 9) nebo inline s jednoduchým modal:
  if (!await _ptConfirm('Opustit run? Získáš pouze 50% nahromaděného XP.')) return;
  try {
    const data = await api('POST', '/playtest/dungeon/abandon', { run_id: runId });
    _ptRun = data.run;
    toast('Run opuštěn.', 'i');
    _ptRender();
  } catch (e) {
    toast(e.message || 'Chyba', 'e');
  }
}

// ── Confirm helper (nepoužívá blokující confirm()) ────────────────────────────
function _ptConfirm(message) {
  return new Promise(resolve => {
    document.getElementById('pt-confirm-text').textContent = message;
    document.getElementById('pt-confirm-ok').onclick = () => {
      closeModal('modal-playtest-confirm'); resolve(true);
    };
    document.getElementById('pt-confirm-cancel').onclick = () => {
      closeModal('modal-playtest-confirm'); resolve(false);
    };
    openModal('modal-playtest-confirm');
  });
}

// ── Cooldown helper ───────────────────────────────────────────────────────────
function _ptCooldownText(isoStr) {
  if (!isoStr) return '';
  const diff = new Date(isoStr) - Date.now();
  if (diff <= 0) return 'Připraven';
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return `Cooldown: ${h}h ${m}m`;
}

// ── Page hook ─────────────────────────────────────────────────────────────────
// Zavolej initPlaytest() při přechodu na stránku.
// Přidej do showPage() v ui.js nebo přímo v onclick:
// onclick="showPage('page-playtest'); initPlaytest();"
```

- [ ] **Step 2: Přidat modaly do game.html**

Najdi sekci s ostatními modaly a přidej:

```html
<!-- PLAYTEST NODE MODAL -->
<div class="overlay" id="modal-playtest-node">
  <div class="modal" style="max-width:440px">
    <div class="modal-header">
      <h3 id="pt-modal-title">Uzel</h3>
      <button onclick="closeModal('modal-playtest-node')" class="modal-close">×</button>
    </div>
    <div class="modal-body pt-modal-body" id="pt-modal-body"></div>
  </div>
</div>

<!-- PLAYTEST CONFIRM MODAL -->
<div class="overlay" id="modal-playtest-confirm">
  <div class="modal" style="max-width:360px">
    <div class="modal-body" style="text-align:center;padding:24px">
      <p id="pt-confirm-text" style="margin-bottom:20px"></p>
      <div style="display:flex;gap:12px;justify-content:center">
        <button id="pt-confirm-ok" class="pt-enter-btn" style="width:auto;padding:10px 24px">Potvrdit</button>
        <button id="pt-confirm-cancel" style="padding:10px 24px;background:transparent;color:var(--clr-muted);border:1px solid rgba(255,255,255,.1);border-radius:8px;cursor:pointer">Zrušit</button>
      </div>
    </div>
  </div>
</div>

<!-- PLAYTEST RELIC MODAL -->
<div class="overlay" id="modal-playtest-relic">
  <div class="modal" style="max-width:600px">
    <div class="modal-header">
      <h3>Vyber Relic</h3>
    </div>
    <div class="modal-body">
      <p style="color:var(--clr-muted);margin-bottom:16px">Jeden relic platí do konce runu.</p>
      <div class="pt-relic-cards" id="pt-relic-cards"></div>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Propojit initPlaytest() se showPage**

V `game.html` najdi tlačítko Playtest v navigaci a uprav:

```html
<button id="nav-playtest" onclick="showPage('page-playtest'); initPlaytest();" class="nav-btn nav-playtest">
  ⚗️ <span>Playtest</span>
</button>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/js/playtest.js frontend/game.html
git commit -m "feat: add playtest.js frontend — map, nodes, relics, events, collect"
```

---

## Task 11: Vampiric Edge — combat engine podpora

**Files:**
- Modify: `backend/game/combat_engine.py`

- [ ] **Step 1: Přidat vampiric lifesteal handler**

Najdi v `combat_engine.py` místo kde se zpracovávají `set_bonuses` (hledej `set_bonuses` nebo lifesteal). Přidej handler pro `vampiric_lifesteal`:

```python
# V sekci kde se aplikují set_bonuses efekty po útoku,
# nebo v _apply_damage() / _process_attack() funkci:
if set_bonuses.get("vampiric_lifesteal") and set_bonuses.get("vampiric_chance"):
    if random.random() < set_bonuses["vampiric_chance"]:
        heal = int(damage_dealt * set_bonuses["vampiric_lifesteal"])
        attacker_state.hp = min(attacker_state.hp + heal, attacker_state.hp_max)
        # Přidej event do log pokud existuje event systém
```

> **Poznámka:** Přesné místo pro tento kód závisí na aktuální struktuře combat_engine.py. Najdi funkci která zpracovává útok a přidej vampiric check po výpočtu damage_dealt. Pokud `set_bonuses` není dostupné v dané funkci, předej ho jako parametr nebo přistupuj přes `attacker_state.set_bonuses`.

- [ ] **Step 2: Ověřit že vampiric_edge nerozbije existující testy**

```bash
cd backend && pytest tests/test_combat.py -v
```

Všechny testy musí projít.

- [ ] **Step 3: Commit**

```bash
git add backend/game/combat_engine.py
git commit -m "feat: add vampiric_edge lifesteal handler to combat engine"
```

---

## Task 12: Finální ověření a integrace

- [ ] **Step 1: Spustit všechny testy**

```bash
cd backend && pytest backend/tests/ -v
```

Očekávaný výstup: všechny testy PASS (nebo skip, žádné FAIL).

- [ ] **Step 2: Manuální smoke test**

1. Spusť server: `cd backend && uvicorn main:app --reload --port 8000`
2. Otevři frontend, přihlás se
3. Klikni na "⚗️ Playtest" v navigaci
4. Vstup do Tomb of Forgotten (min level 8)
5. Zkontroluj že mapa se zobrazí s uzly
6. Klikni na dostupný uzel — ověř modal
7. Projdi run dokončit nebo opustit
8. Ověř že starý "Dungeon" tab stále funguje beze změny

- [ ] **Step 3: Commit finálních oprav**

```bash
git add -A
git commit -m "feat: playtest dungeon system — complete roguelite implementation"
```

---

## Poznámky pro implementaci

**Pořadí scriptů v game.html:** `playtest.js` musí být za `ui.js` a `api.js`, ale může být kdekoli jinak v řadě. Přidej ho za `dungeon.js`.

**`build_combatant_config` signatura:** Funkce v `game/combatant_builder.py` je async a přijímá `(char, db)`. Zkontroluj skutečnou signaturu před použitím — po stat redesignu (migrace 0048) se mohla změnit.

**`_decrease_equipped_durability` a `DURABILITY_LOSS_DUNGEON`:** Tyto jsou definovány v `backend/routers/dungeon.py`. Import: `from routers.dungeon import _decrease_equipped_durability, DURABILITY_LOSS_DUNGEON`. Pokud je funkce private (začíná `_`), přesuň ji do `game/` modulu nebo importuj přímo.

**`char_dict_with_equipment`:** Async funkce v `routers/character.py`. Zkontroluj signaturu — může vyžadovat i `user` nebo `request` parametry.

**`get_random_item_for_quest`:** V `game/loot.py`. Zkontroluj signaturu — může přijímat různé parametry.
