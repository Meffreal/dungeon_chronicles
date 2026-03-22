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
from models.item import InventoryItem
from models.playtest_run import PlaytestRun
from models.economy import log_gold, GoldReason
from routers.auth import get_current_user
from game.playtest_dungeon import (
    PLAYTEST_DUNGEONS, generate_map, get_available_nodes,
    unlock_successors, roll_relics, apply_relic_to_run,
    apply_event_choice, build_enemy_config, build_playtest_combatant,
    calculate_node_rewards, DUNGEON_EVENTS,
)
from game.combat_engine import simulate_unified_combat, events_to_dict_list
from game.loot import get_random_item_for_quest
from routers.dungeon import _trigger_permadeath

router = APIRouter(prefix="/playtest/dungeon", tags=["playtest"])


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _run_dict(run: PlaytestRun) -> dict:
    return {
        "id":              run.id,
        "dungeon_key":     run.dungeon_key,
        "status":          run.status,
        "hp_current":      run.hp_current,
        "hp_max":          run.hp_max,
        "run_gold":        run.run_gold,
        "reward_xp":       run.reward_xp,
        "reward_gold":     run.reward_gold,
        "reward_claimed":  run.reward_claimed,
        "relics":          run.get_relics(),
        "pending_relics":  run.get_pending_relics(),
        "current_node_id": run.current_node_id,
        "visited_nodes":   run.get_visited(),
        "map_data":        run.get_map(),
        "cooldown_until":  run.cooldown_until.isoformat() if run.cooldown_until else None,
    }


# ── GET /list ─────────────────────────────────────────────────────────────────

@router.get("/list")
async def playtest_dungeon_list(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    active_run = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id, PlaytestRun.status == "active")
        .order_by(PlaytestRun.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    recent_runs = (await db.execute(
        select(PlaytestRun)
        .where(
            PlaytestRun.char_id == char.id,
            PlaytestRun.cooldown_until != None,
        )
        .order_by(PlaytestRun.created_at.desc())
    )).scalars().all()

    cooldowns: dict = {}
    for r in recent_runs:
        if r.dungeon_key not in cooldowns:
            cooldowns[r.dungeon_key] = r.cooldown_until

    now = _now()
    dungeons = []
    for key, cfg in PLAYTEST_DUNGEONS.items():
        cd = cooldowns.get(key)
        on_cooldown = bool(cd and cd > now)
        locked = char.level < cfg["min_level"]
        dungeons.append({
            "key":            key,
            "name":           cfg["name"],
            "min_level":      cfg["min_level"],
            "cooldown_hours": cfg["cooldown_hours"],
            "boss_mult":      cfg["boss_mult"],
            "locked":         locked,
            "on_cooldown":    on_cooldown,
            "cooldown_until": cd.isoformat() if on_cooldown else None,
        })

    return {
        "dungeons":   dungeons,
        "active_run": _run_dict(active_run) if active_run else None,
        "char_level": char.level,
    }


# ── GET /status ───────────────────────────────────────────────────────────────

@router.get("/status")
async def playtest_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id, PlaytestRun.status == "active")
        .limit(1)
    )).scalar_one_or_none()

    return {"run": _run_dict(run) if run else None}


# ── POST /enter ───────────────────────────────────────────────────────────────

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
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    cfg = PLAYTEST_DUNGEONS[body.dungeon_key]

    if char.level < cfg["min_level"]:
        raise HTTPException(400, f"Minimální úroveň {cfg['min_level']}")

    last_run = (await db.execute(
        select(PlaytestRun)
        .where(
            PlaytestRun.char_id == char.id,
            PlaytestRun.dungeon_key == body.dungeon_key,
            PlaytestRun.cooldown_until != None,
        )
        .order_by(PlaytestRun.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    now = _now()
    if last_run and last_run.cooldown_until and last_run.cooldown_until > now:
        raise HTTPException(
            400,
            f"Dungeon na cooldownu do {last_run.cooldown_until.isoformat()}",
        )

    existing = (await db.execute(
        select(PlaytestRun)
        .where(PlaytestRun.char_id == char.id, PlaytestRun.status == "active")
        .limit(1)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            400,
            "Máš aktivní Playtest run. Dokonči nebo opusť ho nejdříve.",
        )

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
    run.set_pending_relics([])
    run.visited_nodes = "[]"
    db.add(run)
    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při vstupu do dungeonu — zkus znovu.")

    return {"run": _run_dict(run)}


# ── POST /choose-node ─────────────────────────────────────────────────────────

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
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(
            PlaytestRun.id == body.run_id,
            PlaytestRun.char_id == char.id,
            PlaytestRun.status == "active",
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Aktivní run nenalezen")

    mdata = run.get_map()
    nodes = mdata.get("nodes", {})

    if body.node_id not in nodes:
        raise HTTPException(400, "Uzel neexistuje")

    node = nodes[body.node_id]
    available = get_available_nodes(mdata)
    if body.node_id not in available:
        raise HTTPException(400, "Uzel není dostupný")

    # Mark node visited and set as current
    visited = run.get_visited()
    if body.node_id not in visited:
        visited.append(body.node_id)
    run.visited_nodes = json.dumps(visited)
    run.current_node_id = body.node_id
    node["status"] = "completed"

    node_type = node["type"]
    cfg = PLAYTEST_DUNGEONS[run.dungeon_key]

    # ── Rest node ─────────────────────────────────────────────────────────────
    if node_type == "rest":
        healed = int(run.hp_max * 0.25)
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        unlock_successors(mdata, body.node_id)
        run.set_map(mdata)
        try:
            await db.commit()
            await db.refresh(run)
        except Exception:
            await db.rollback()
            raise HTTPException(500, "Chyba — zkus znovu.")
        return {
            "node_type":  "rest",
            "hp_healed":  healed,
            "run":        _run_dict(run),
        }

    # ── Event node ────────────────────────────────────────────────────────────
    if node_type == "event":
        node["status"] = "pending_event"   # override — awaiting player choice
        event_id = node.get("event_id")
        events_list = DUNGEON_EVENTS.get(run.dungeon_key, DUNGEON_EVENTS["pt_tomb"])
        event = next((e for e in events_list if e["id"] == event_id), None)
        run.set_map(mdata)
        try:
            await db.commit()
            await db.refresh(run)
        except Exception:
            await db.rollback()
            raise HTTPException(500, "Chyba — zkus znovu.")
        return {
            "node_type": "event",
            "event_id":  event_id,
            "event":     event,
            "run":       _run_dict(run),
        }

    # ── Shop node ─────────────────────────────────────────────────────────────
    if node_type == "shop":
        if body.skip_shop:
            unlock_successors(mdata, body.node_id)
            run.set_map(mdata)
            try:
                await db.commit()
                await db.refresh(run)
            except Exception:
                await db.rollback()
                raise HTTPException(500, "Chyba — zkus znovu.")
            return {
                "node_type": "shop",
                "skipped":   True,
                "run":       _run_dict(run),
            }
        shop_items = [
            {"id": "heal",          "name": "Léčení",          "cost": 50,  "desc": "Obnov 40% HP"},
            {"id": "atk_boost",     "name": "Síla hrdinů",      "cost": 80,  "desc": "+10% ATK do konce runu"},
            {"id": "relic_refresh", "name": "Refresh reliců",   "cost": 120, "desc": "Nové 3 relic nabídky"},
        ]
        run.set_map(mdata)
        try:
            await db.commit()
            await db.refresh(run)
        except Exception:
            await db.rollback()
            raise HTTPException(500, "Chyba — zkus znovu.")
        return {
            "node_type":  "shop",
            "shop_items": shop_items,
            "run":        _run_dict(run),
        }

    # ── Combat / Elite / Boss nodes ───────────────────────────────────────────
    if node_type not in ("combat", "elite", "boss"):
        raise HTTPException(400, f"Neznámý typ uzlu: {node_type}")

    # Apply pending boost from event if present
    pending_boost = mdata.pop("pending_boost", None)
    if pending_boost:
        orig_mult = node.get("enemy_mult", 1.0)
        node["enemy_mult"] = round(orig_mult * pending_boost["mult"], 3)
        reward_mult = pending_boost.get("reward_mult", 1.0)
        node["reward_xp"]   = int(node.get("reward_xp",   cfg["xp_base"])   * reward_mult)
        node["reward_gold"] = int(node.get("reward_gold", cfg["gold_base"]) * reward_mult)

    player_cfg = await build_playtest_combatant(char, run, db)
    enemy_cfg  = build_enemy_config(run.dungeon_key, node, char.level)

    result = simulate_unified_combat(player_cfg, enemy_cfg)

    combat_log  = events_to_dict_list(result.events)
    is_boss     = node_type == "boss"
    now         = _now()
    permadeath_data = None

    if result.attacker_won:
        # Calculate rewards
        xp_earned, gold_earned = calculate_node_rewards(
            node, run.get_relics(), cfg["xp_base"], cfg["gold_base"]
        )
        run.reward_xp   += xp_earned
        run.reward_gold += gold_earned
        run.run_gold    += gold_earned
        run.hp_current   = max(1, result.attacker_hp_remaining)

        # Roll relics — successors unlocked only after choose-relic
        is_elite = node_type == "elite"
        existing_ids = [r["id"] for r in run.get_relics()]
        pending = roll_relics(existing_ids, is_elite=is_elite)
        run.set_pending_relics(pending)

        if is_boss:
            run.cooldown_until = now + timedelta(hours=cfg["cooldown_hours"])
        # Successors unlocked via /choose-relic (status set to "completed" there for boss)

        run.set_map(mdata)

        # Per-combat hooks
        await _fire_combat_hooks(char, db)

        try:
            await db.commit()
            await db.refresh(run)
            await db.refresh(char)
        except Exception:
            await db.rollback()
            raise HTTPException(500, "Chyba po boji — zkus znovu.")

        return {
            "node_type":     node_type,
            "won":           True,
            "xp_earned":     xp_earned,
            "gold_earned":   gold_earned,
            "combat_log":    combat_log,
            "pending_relics": pending,
            "run":           _run_dict(run),
        }

    else:
        # Loss
        run.hp_current = 0
        run.status     = "failed"
        run.cooldown_until = now + timedelta(hours=cfg["cooldown_hours"])
        run.set_map(mdata)

        if char.is_hardcore:
            permadeath_data = await _trigger_permadeath(
                char, node.get("enemy_name", "Unknown"), run.dungeon_key, now, db
            )

        try:
            await db.commit()
            await db.refresh(run)
        except Exception:
            await db.rollback()
            raise HTTPException(500, "Chyba po prohře — zkus znovu.")

        return {
            "node_type":      node_type,
            "won":            False,
            "combat_log":     combat_log,
            "run":            _run_dict(run),
            "permadeath":     permadeath_data,
        }


# ── POST /choose-event ────────────────────────────────────────────────────────

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
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(
            PlaytestRun.id == body.run_id,
            PlaytestRun.char_id == char.id,
            PlaytestRun.status == "active",
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Aktivní run nenalezen")

    if not run.current_node_id:
        raise HTTPException(400, "Žádný aktuální uzel")

    mdata = run.get_map()
    node  = mdata["nodes"].get(run.current_node_id, {})
    if node.get("status") != "pending_event":
        raise HTTPException(400, "Aktuální uzel není event")

    event_id = node.get("event_id")
    result = apply_event_choice(run, run.dungeon_key, event_id, body.choice_index)

    # Mark completed and unlock successors
    node["status"] = "completed"
    unlock_successors(mdata, run.current_node_id)
    run.set_map(mdata)

    # If event granted pending relics, persist them
    if result.get("pending_relics"):
        existing = run.get_pending_relics()
        existing.extend(result["pending_relics"])
        run.set_pending_relics(existing)

    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při výběru možnosti — zkus znovu.")

    return {
        "outcome_text":  result["outcome_text"],
        "hp_delta":      result["hp_delta"],
        "gold_delta":    result["gold_delta"],
        "pending_relics": result.get("pending_relics"),
        "run":           _run_dict(run),
    }


# ── POST /choose-relic ────────────────────────────────────────────────────────

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
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(
            PlaytestRun.id == body.run_id,
            PlaytestRun.char_id == char.id,
            PlaytestRun.status.in_(["active", "completed"]),
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run nenalezen")

    pending = run.get_pending_relics()
    chosen = next((r for r in pending if r["id"] == body.relic_id), None)
    if not chosen:
        raise HTTPException(400, "Relic není v nabídce")

    # Add chosen relic to active relics, then apply one-time effects
    relics = run.get_relics()
    relics.append(chosen)
    run.set_relics(relics)

    # Apply one-time effects (e.g. hp_restore_pct); re-save with consumed flag
    apply_result = apply_relic_to_run(run, chosen)
    run.set_relics(relics)  # persist consumed flag per docstring

    # Clear pending relics
    run.set_pending_relics([])

    # Check if current node is boss — if so, complete the run; otherwise unlock successors
    if run.current_node_id:
        mdata = run.get_map()
        current_node = mdata["nodes"].get(run.current_node_id, {})
        if current_node.get("type") == "boss":
            run.status = "completed"
            await _fire_completion_hooks(char, db, run.dungeon_key)
        else:
            if run.status == "active":
                unlock_successors(mdata, run.current_node_id)
        run.set_map(mdata)

    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při výběru relicu — zkus znovu.")

    return {
        "relic":      chosen,
        "hp_delta":   apply_result["hp_delta"],
        "run":        _run_dict(run),
    }


# ── POST /shop-buy ────────────────────────────────────────────────────────────

class ShopBuyRequest(BaseModel):
    run_id:  int
    item_id: str  # "heal" | "atk_boost" | "relic_refresh"


SHOP_ITEMS = {
    "heal":          {"cost": 50,  "name": "Léčení"},
    "atk_boost":     {"cost": 80,  "name": "Síla hrdinů"},
    "relic_refresh": {"cost": 120, "name": "Refresh reliců"},
}


@router.post("/shop-buy")
async def playtest_shop_buy(
    body: ShopBuyRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.item_id not in SHOP_ITEMS:
        raise HTTPException(400, "Neznámý item")

    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(
            PlaytestRun.id == body.run_id,
            PlaytestRun.char_id == char.id,
            PlaytestRun.status == "active",
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Aktivní run nenalezen")

    shop_cfg = SHOP_ITEMS[body.item_id]
    cost = shop_cfg["cost"]

    if run.run_gold < cost:
        raise HTTPException(400, f"Nedostatek gold v runu (potřeba {cost}g)")

    run.run_gold -= cost
    effect: dict = {}

    if body.item_id == "heal":
        healed = int(run.hp_max * 0.40)
        run.hp_current = min(run.hp_current + healed, run.hp_max)
        effect = {"hp_healed": healed}

    elif body.item_id == "atk_boost":
        boost = {
            "id":         "shop_atk_boost",
            "name":       "Síla hrdinů",
            "effect_key": "atk_pct",
            "value":      0.10,
            "desc":       "+10% ATK (shop)",
        }
        relics = run.get_relics()
        relics.append(boost)
        run.set_relics(relics)
        effect = {"relic_added": boost}

    elif body.item_id == "relic_refresh":
        existing_ids = [r["id"] for r in run.get_relics()]
        new_pending  = roll_relics(existing_ids)
        run.set_pending_relics(new_pending)
        effect = {"pending_relics": new_pending}

    # Unlock shop node successors
    if run.current_node_id:
        mdata = run.get_map()
        node  = mdata["nodes"].get(run.current_node_id, {})
        if node.get("type") == "shop" and node.get("status") != "completed":
            node["status"] = "completed"
            unlock_successors(mdata, run.current_node_id)
            run.set_map(mdata)

    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při nákupu — zkus znovu.")

    return {
        "item_id": body.item_id,
        "cost":    cost,
        "effect":  effect,
        "run":     _run_dict(run),
    }


# ── POST /collect ─────────────────────────────────────────────────────────────

class CollectRequest(BaseModel):
    run_id: int


@router.post("/collect")
async def playtest_collect(
    req: CollectRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(
            PlaytestRun.id == req.run_id,
            PlaytestRun.char_id == char.id,
            PlaytestRun.status.in_(["completed", "failed"]),
            PlaytestRun.reward_claimed == False,
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Žádný run čeká na vyzvednutí")

    xp_gained   = run.reward_xp
    gold_to_pay = run.run_gold if run.status == "completed" else 0

    char.xp   += xp_gained
    char.gold += gold_to_pay
    if gold_to_pay > 0:
        await log_gold(
            db, char, gold_to_pay, GoldReason.DUNGEON_REWARD,
            {"playtest_run_id": run.id, "dungeon_key": run.dungeon_key},
        )

    # Level-up loop
    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        leveled_up.append(char.level)
    if leveled_up:
        from routers.inventory import recalculate_with_gear
        await recalculate_with_gear(char, db)

    # Boss loot drop on completion
    gained_item = None
    if run.status == "completed":
        drop_item = await get_random_item_for_quest(db, "hard", char.level)
        if drop_item:
            inv_result = await db.execute(
                select(InventoryItem).where(
                    InventoryItem.character_id == char.id,
                    InventoryItem.item_id == drop_item.id,
                )
            )
            inv_item = inv_result.scalar_one_or_none()
            if inv_item:
                inv_item.quantity += 1
            else:
                inv_item = InventoryItem(
                    character_id=char.id,
                    item_id=drop_item.id,
                    quantity=1,
                )
                db.add(inv_item)
            gained_item = drop_item.to_dict()

    run.reward_claimed = True

    try:
        await db.commit()
        await db.refresh(char)
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při vyzvednutí odměn — zkus znovu.")

    return {
        "message":    "Odměny vyzvednuty!",
        "completed":  run.status == "completed",
        "xp_gained":  xp_gained,
        "gold_gained": gold_to_pay,
        "leveled_up": leveled_up,
        "gained_item": gained_item,
        "run":        _run_dict(run),
    }


# ── POST /abandon ─────────────────────────────────────────────────────────────

class AbandonRequest(BaseModel):
    run_id: int


@router.post("/abandon")
async def playtest_abandon(
    req: AbandonRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    char = (await db.execute(
        select(Character).where(Character.user_id == current_user.id, Character.is_dead == False)
    )).scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena")

    run = (await db.execute(
        select(PlaytestRun).where(
            PlaytestRun.id == req.run_id,
            PlaytestRun.char_id == char.id,
            PlaytestRun.status == "active",
        )
    )).scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Žádný aktivní run")

    cfg = PLAYTEST_DUNGEONS.get(run.dungeon_key, {})
    cd_hours = cfg.get("cooldown_hours", 6)
    now = _now()

    # 50% XP partial payout
    run.reward_xp   = run.reward_xp // 2
    run.status      = "failed"
    run.run_gold    = 0
    run.reward_gold = 0
    run.cooldown_until = now + timedelta(hours=max(1, cd_hours // 4))

    try:
        await db.commit()
        await db.refresh(run)
    except Exception:
        await db.rollback()
        raise HTTPException(500, "Chyba při opuštění runu — zkus znovu.")

    return {
        "message": "Run opuštěn.",
        "run":     _run_dict(run),
    }


# ── Hook helpers ──────────────────────────────────────────────────────────────

async def _fire_combat_hooks(char: Character, db: AsyncSession) -> None:
    """Per-combat win hooks: kills, durability, season XP."""
    try:
        from routers.guild import increment_guild_weekly
        if char.guild_id:
            await increment_guild_weekly(char.guild_id, "kills", 1, char.id, db)
    except Exception:
        pass

    try:
        from routers.weekly_quest import increment_weekly_board
        await increment_weekly_board(char.id, "kills", 1, db)
    except Exception:
        pass

    try:
        from routers.season_pass import add_season_xp
        await add_season_xp(char.id, "dungeon_stage", db)
    except Exception:
        pass

    try:
        from routers.inventory import _decrease_equipped_durability, DURABILITY_LOSS_DUNGEON
        await _decrease_equipped_durability(char, DURABILITY_LOSS_DUNGEON, db)
    except Exception:
        pass


async def _fire_completion_hooks(
    char: Character, db: AsyncSession, dungeon_key: str
) -> None:
    """Run completion hooks: guild dungeons, weekly board, season XP."""
    try:
        from routers.guild import increment_guild_weekly
        if char.guild_id:
            await increment_guild_weekly(char.guild_id, "dungeons", 1, char.id, db)
    except Exception:
        pass

    try:
        from routers.weekly_quest import increment_weekly_board
        await increment_weekly_board(char.id, "dungeons", 1, db)
    except Exception:
        pass

    try:
        from routers.season_pass import add_season_xp
        await add_season_xp(char.id, "dungeon_complete", db)
    except Exception:
        pass

    try:
        from routers.world_event import add_world_event_contribution
        await add_world_event_contribution("dungeon_clears", char.id, 1, db)
    except Exception:
        pass
