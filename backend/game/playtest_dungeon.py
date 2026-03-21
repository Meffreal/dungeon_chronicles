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
# Fiery and Citadel share Tomb events for MVP
DUNGEON_EVENTS["pt_fiery"] = DUNGEON_EVENTS["pt_tomb"]
DUNGEON_EVENTS["pt_citadel"] = DUNGEON_EVENTS["pt_tomb"]

# ── Generátor mapy ────────────────────────────────────────────────────────────

def generate_map(dungeon_key: str, char_level: int) -> dict:
    """
    Generate procedural map for a dungeon run.
    Structure: Start → [Layer1: 2 nodes] → [Layer2: 2 nodes] → [Layer3: 2 nodes] → Boss
    Each layer has 2 nodes, player picks one, the other is skipped.
    """
    cfg = PLAYTEST_DUNGEONS[dungeon_key]
    nodes = {}
    edges = []
    layout = {}

    # Start node
    nodes["start"] = {"type": "start", "status": "completed"}
    layout["start"] = [0, 0]

    # Layer 1: combat + (rest or event)
    l1_left  = _make_combat_node(cfg, char_level, "n1a")
    l1_right_type = random.choice(["rest", "event"])
    l1_right = _make_node(l1_right_type, cfg, char_level, "n1b", dungeon_key)
    nodes["n1a"] = l1_left
    nodes["n1b"] = l1_right
    layout["n1a"] = [1, -1]
    layout["n1b"] = [1, 1]
    edges += [["start", "n1a"], ["start", "n1b"]]
    # Layer 1 nodes are immediately available
    nodes["n1a"]["status"] = "available"
    nodes["n1b"]["status"] = "available"

    # Layer 2: (combat or elite) + (event or shop)
    l2_left_type  = random.choice(["combat", "elite"])
    l2_right_type = random.choice(["event", "shop"])
    l2_left  = _make_node(l2_left_type,  cfg, char_level, "n2a", dungeon_key)
    l2_right = _make_node(l2_right_type, cfg, char_level, "n2b", dungeon_key)
    nodes["n2a"] = l2_left
    nodes["n2b"] = l2_right
    layout["n2a"] = [2, -1]
    layout["n2b"] = [2, 1]
    edges += [["n1a", "n2a"], ["n1a", "n2b"], ["n1b", "n2a"], ["n1b", "n2b"]]

    # Layer 3: elite + (rest or combat)
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
    _apply_constraint_fixes(map_data, cfg, char_level, dungeon_key)
    return map_data


def _make_combat_node(cfg: dict, char_level: int, node_id: str) -> dict:
    enemy_name, enemy_mult = random.choice(cfg["enemy_pool"])
    xp   = int(cfg["xp_base"]   * char_level * enemy_mult)
    gold = int(cfg["gold_base"]  * char_level * enemy_mult)
    return {"type": "combat", "enemy_name": enemy_name, "enemy_mult": enemy_mult,
            "status": "locked", "reward_xp": xp, "reward_gold": gold}


def _make_node(node_type: str, cfg: dict, char_level: int, node_id: str, dungeon_key: str = "pt_tomb") -> dict:
    """dungeon_key must be passed explicitly — cfg dict does not contain its own key."""
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


def _apply_constraint_fixes(map_data: dict, cfg: dict, char_level: int, dungeon_key: str):
    """Force-substitute if constraints are not met.

    Runs in a loop until all constraints are satisfied, to handle cases where
    fixing one constraint would otherwise break another (e.g. event fix clobbering
    the only rest node).
    """
    nodes = map_data["nodes"]

    for _ in range(4):  # max iterations; typically 1–2 suffice
        types = [n["type"] for n in nodes.values()]
        changed = False

        if "rest" not in types:
            # Prefer n3b; fall back to n1b only if n3b is already elite
            target = "n3b" if nodes.get("n3b", {}).get("type") != "elite" else "n1b"
            nodes[target] = _make_node("rest", cfg, char_level, target, dungeon_key)
            changed = True

        types = [n["type"] for n in nodes.values()]
        if "elite" not in types:
            nodes["n2a"] = _make_node("elite", cfg, char_level, "n2a", dungeon_key)
            changed = True

        types = [n["type"] for n in nodes.values()]
        if "event" not in types:
            # Pick a node that isn't currently providing rest or elite
            for candidate in ("n1b", "n2b", "n3b"):
                if nodes.get(candidate, {}).get("type") not in ("rest", "elite", "boss", "start"):
                    nodes[candidate] = _make_node("event", cfg, char_level, candidate, dungeon_key)
                    break
            changed = True

        if not changed:
            break


def get_available_nodes(map_data: dict) -> list:
    """Return IDs of nodes with status 'available'."""
    return [nid for nid, n in map_data["nodes"].items() if n["status"] == "available"]


def unlock_successors(map_data: dict, completed_node_id: str):
    """Unlock successors of completed node (locked → available)."""
    nodes = map_data["nodes"]
    edges = map_data["edges"]

    for src, dst in edges:
        if src == completed_node_id and nodes.get(dst, {}).get("status") == "locked":
            nodes[dst]["status"] = "available"

# ── Relic helpers ─────────────────────────────────────────────────────────────

def roll_relics(existing_relic_ids: list, is_elite: bool = False, count: int = 3) -> list:
    """Pick count random relics from pool. Don't include relics player already has."""
    pool = ELITE_RELIC_POOL if is_elite else RELIC_POOL
    available = [r for r in pool if r["id"] not in existing_relic_ids]
    if len(available) < count:
        available = pool  # fallback
    return random.sample(available, min(count, len(available)))


def apply_relic_to_run(run, relic: dict) -> dict:
    """
    Apply one-time relic effects immediately.
    IMPORTANT: relic is modified in-place (consumed flag).
    Caller MUST call run.set_relics(updated_list) after calling this function
    to persist the consumed state. The relic dict should come from run.get_relics()
    and be part of the list that is re-saved.

    Correct call pattern in router:
        relics = run.get_relics()
        relic_from_list = next(r for r in relics if r["id"] == chosen_id)
        result = apply_relic_to_run(run, relic_from_list)
        run.set_relics(relics)  # persist consumed flag

    Passive effects (atk_pct, def_pct, etc.) are applied each combat in
    build_playtest_combatant — they must NOT be consumed.
    Returns dict describing what happened (for frontend).
    """
    result = {"hp_delta": 0, "description": relic["desc"]}

    if relic["effect_key"] == "hp_restore_pct":
        healed = int(run.hp_max * relic["value"])
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        result["hp_delta"] = healed
        relic["consumed"] = True  # one-time effect

    elif relic["effect_key"] == "hp_max_pct":
        # iron_will — increase hp_max but do NOT heal
        run.hp_max = int(run.hp_max * (1 + relic["value"]))

    return result

# ── Combat builder ────────────────────────────────────────────────────────────

async def build_playtest_combatant(char, run, db):
    """
    Build CombatantConfig for player with relic effects applied.
    Uses build_combatant_config as base then applies relics.
    """
    from game.combatant_builder import build_combatant_config

    # Base from existing builder (reads equipment, stats, etc.)
    base_cfg = await build_combatant_config(char, db)

    # Override HP with current run state
    base_cfg.hp = run.hp_current

    # Apply passive relic effects
    relics = run.get_relics()
    for relic in relics:
        if relic.get("consumed"):
            continue
        key = relic["effect_key"]
        val = relic["value"]

        if key == "atk_pct":
            base_cfg.weapon_dmg   = int(base_cfg.weapon_dmg   * (1 + val))
            base_cfg.primary_stat = int(base_cfg.primary_stat * (1 + val))
        elif key == "def_pct":
            base_cfg.armor_value = int(base_cfg.armor_value * (1 + val))
        elif key == "atk_spd_pct":
            # war_cry: +ATK via weapon_dmg and primary_stat.
            # CombatantConfig has no direct spd field — speed is derived from
            # secondary stats inside the combat engine (class-specific mapping).
            # SPD component of war_cry is therefore a no-op at config level.
            base_cfg.weapon_dmg   = int(base_cfg.weapon_dmg   * (1 + val))
            base_cfg.primary_stat = int(base_cfg.primary_stat * (1 + val))
        elif key == "spd_pct":
            # swift_boots: CombatantConfig has no direct spd field — speed is
            # derived from secondary stats inside the engine. No-op at this layer.
            pass
        elif key == "mp_pct":
            # mana_crystal: CombatantConfig has no mp field — MP (mana) is not
            # exposed as an input field in CombatantConfig. No-op at this layer.
            pass
        elif key == "luck_pct":
            base_cfg.luck = int(base_cfg.luck * (1 + val))
        elif key == "cursed_blade":
            base_cfg.weapon_dmg   = int(base_cfg.weapon_dmg   * (1 + val))
            base_cfg.primary_stat = int(base_cfg.primary_stat * (1 + val))
            base_cfg.armor_value  = int(base_cfg.armor_value  * 0.90)
        elif key == "vampiric_edge":
            existing = base_cfg.set_bonuses or {}
            base_cfg.set_bonuses = {**existing, "vampiric_lifesteal": 0.15, "vampiric_chance": 0.10}

    return base_cfg


def build_enemy_config(dungeon_key: str, node: dict, char_level: int):
    """Build CombatantConfig for enemy from node data."""
    from game.combat_engine import CombatantConfig

    cfg  = PLAYTEST_DUNGEONS[dungeon_key]
    mult = node["enemy_mult"]
    lvl  = max(char_level, cfg.get("min_level", 1))

    is_boss = node["type"] == "boss"
    return CombatantConfig(
        name         = node["enemy_name"],
        hp           = int(60  * lvl * mult),
        weapon_dmg   = int(9   * lvl * mult),
        armor_value  = int(5   * lvl * mult),
        primary_stat = int(8   * lvl * mult),
        secondary_a  = int(6   * lvl * mult),
        secondary_b  = int(4   * lvl * mult),
        luck         = 5,
        level        = lvl,
        cls          = "enemy",
        is_boss      = is_boss,
    )


def calculate_node_rewards(node: dict, relics: list, xp_base: int, gold_base: int) -> tuple:
    """Calculate XP and gold reward from node with relic bonuses."""
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

# ── Event handler ─────────────────────────────────────────────────────────────

def apply_event_choice(run, dungeon_key: str, event_id: str, choice_index: int) -> dict:
    """Apply event choice result. Returns dict with outcome info."""
    events_list = DUNGEON_EVENTS.get(dungeon_key, DUNGEON_EVENTS["pt_tomb"])
    event = next((e for e in events_list if e["id"] == event_id), None)
    if not event:
        return {"outcome_text": "Nic se nestalo.", "hp_delta": 0, "gold_delta": 0}

    outcomes = event["outcomes"].get(choice_index, [{"weight": 100, "type": "nothing", "text": "Nic."}])
    # Weighted random selection
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
        result["hp_delta"]       = -loss
        existing_ids             = [r["id"] for r in run.get_relics()]
        result["pending_relics"] = roll_relics(existing_ids, count=1)
    elif otype == "hp_loss_and_atk":
        loss = int(run.hp_max * chosen["percent"])
        run.hp_current = max(0, run.hp_current - loss)
        result["hp_delta"] = -loss
        boost = {"id": "event_atk_boost", "name": "Krvavá smlouva",
                 "effect_key": "atk_pct", "value": chosen["atk_bonus"],
                 "desc": f"+{int(chosen['atk_bonus']*100)}% ATK (event)"}
        relics = run.get_relics()
        relics.append(boost)
        run.set_relics(relics)
    elif otype == "next_node_boost":
        mdata = run.get_map()
        mdata["pending_boost"] = {"mult": chosen["mult"], "reward_mult": chosen["reward_mult"]}
        run.set_map(mdata)

    return result
