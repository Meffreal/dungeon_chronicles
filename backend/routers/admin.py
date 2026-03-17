"""
routers/admin.py — Admin panel
Chráněno statickým klíčem v hlavičce X-Admin-Key.
"""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, union_all, union
from sqlalchemy.orm import selectinload, aliased
from typing import Literal
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.character import Character
from models.quest import Quest, QuestStatus, QUEST_DEFINITIONS
from models.disabled_quest import get_disabled_quest_ids, disable_quest, enable_quest
from models.arena import ArenaMatch, Season
from models.guild import Guild
from models.market import MarketListing
from models.achievement import PlayerAchievement
from models.item import InventoryItem, Item
from models.economy import GoldTransaction, log_gold, GoldReason
from models.notification import Notification, NotifType
from models.world_event import WorldEvent, WorldEventContrib, WORLD_EVENT_DEFINITIONS
from models.world_boss import WorldBoss, BossParticipation, WORLD_BOSS_DEFINITIONS
from models.scheduled_crystal_sale import ScheduledCrystalSale
from models.crystal import CRYSTAL_SHOP
from models.experiment import Experiment, OVERRIDABLE_PARAMS
from models.balance_alert import BalanceAlert
from models.bug_report import BugReport
from game.experiments import invalidate_experiment_cache

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_KEY = os.getenv("ADMIN_KEY", "dungeon-admin-2024")


def _check_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(403, "Neplatný admin klíč.")


# ── Přehled hry ───────────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(_check_key)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    """Celkové statistiky hry."""
    users_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    chars_count = (await db.execute(select(func.count()).select_from(Character))).scalar_one()
    guilds_count = (await db.execute(select(func.count()).select_from(Guild))).scalar_one()
    active_quests = (await db.execute(
        select(func.count()).select_from(Quest).where(Quest.status == QuestStatus.ACTIVE)
    )).scalar_one()
    total_matches = (await db.execute(select(func.count()).select_from(ArenaMatch))).scalar_one()
    active_listings = (await db.execute(
        select(func.count()).select_from(MarketListing).where(MarketListing.is_sold == False)
    )).scalar_one()
    achievements_awarded = (await db.execute(select(func.count()).select_from(PlayerAchievement))).scalar_one()

    top_chars_res = await db.execute(
        select(Character).order_by(Character.level.desc(), Character.xp.desc()).limit(5)
    )
    top_chars = top_chars_res.scalars().all()

    season_res = await db.execute(select(Season).where(Season.is_active == True).order_by(Season.id.desc()))
    season = season_res.scalar_one_or_none()

    return {
        "overview": {
            "users":               users_count,
            "characters":          chars_count,
            "guilds":              guilds_count,
            "active_quests":       active_quests,
            "arena_matches_total": total_matches,
            "market_listings":     active_listings,
            "achievements_given":  achievements_awarded,
        },
        "top_characters": [
            {"name": c.name, "cls": c.cls, "level": c.level, "gold": c.gold, "elo": c.arena_rank}
            for c in top_chars
        ],
        "current_season": season.to_dict() if season else None,
    }


@router.get("/users", dependencies=[Depends(_check_key)])
async def admin_users(db: AsyncSession = Depends(get_db)):
    """Seznam všech uživatelů + jejich postava."""
    users_res = await db.execute(select(User).order_by(User.created_at.desc()))
    users = users_res.scalars().all()

    out = []
    for u in users:
        char_res = await db.execute(select(Character).where(Character.user_id == u.id))
        char = char_res.scalar_one_or_none()
        out.append({
            "id":         u.id,
            "username":   u.username,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "character":  {
                "name":  char.name,
                "cls":   char.cls,
                "level": char.level,
                "gold":  char.gold,
            } if char else None,
        })

    return {"users": out, "total": len(out)}


# ── Player lookup ─────────────────────────────────────────────────────────────

@router.get("/player/{name}", dependencies=[Depends(_check_key)])
async def admin_player(name: str, db: AsyncSession = Depends(get_db)):
    """Detail hráče: stav, gold, equipment, inventář, quest, arena."""
    char_res = await db.execute(select(Character).where(Character.name == name))
    char = char_res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, f"Postava '{name}' nenalezena.")

    # Inventář
    inv_res = await db.execute(
        select(InventoryItem)
        .options(selectinload(InventoryItem.item))
        .where(InventoryItem.character_id == char.id)
        .order_by(InventoryItem.id.desc())
        .limit(20)
    )
    inventory = inv_res.scalars().all()

    # Quest stav
    quest_res = await db.execute(select(Quest).where(Quest.character_id == char.id))
    quest = quest_res.scalar_one_or_none()

    # Poslední transakce
    tx_res = await db.execute(
        select(GoldTransaction)
        .where(GoldTransaction.character_id == char.id)
        .order_by(GoldTransaction.timestamp.desc())
        .limit(10)
    )
    transactions = tx_res.scalars().all()

    # Arena zápasy
    matches_res = await db.execute(
        select(func.count()).select_from(ArenaMatch).where(
            (ArenaMatch.attacker_id == char.id) | (ArenaMatch.defender_id == char.id)
        )
    )
    total_matches = matches_res.scalar_one()

    equipped_ids = {
        char.eq_weapon, char.eq_helmet, char.eq_armor,
        char.eq_gloves, char.eq_boots, char.eq_ring, char.eq_amulet,
    } - {None}

    return {
        "character": {
            "id":              char.id,
            "name":            char.name,
            "cls":             char.cls,
            "level":           char.level,
            "xp":              char.xp,
            "gold":            char.gold,
            "hp_max":          char.hp_max,
            "luck":            char.luck,
            "arena_rank":      char.arena_rank,
            "quests_completed": char.quests_completed or 0,
            "guild_id":        char.guild_id,
            "faction":         char.faction,
            "stat_points":     char.stat_points or 0,
        },
        "quest": {
            "status":   quest.status if quest else "idle",
            "quest_id": quest.quest_def_id if quest else None,
        },
        "inventory": [
            {
                "item_name": inv.item.name if inv.item else "?",
                "rarity":    inv.item.rarity if inv.item else "?",
                "qty":       inv.quantity,
                "equipped":  inv.item_id in equipped_ids,
            }
            for inv in inventory
        ],
        "recent_gold_transactions": [
            {
                "amount":    tx.amount,
                "reason":    tx.reason,
                "balance_after": tx.balance_after,
                "timestamp": tx.timestamp.isoformat() if tx.timestamp else None,
            }
            for tx in transactions
        ],
        "arena_matches_total": total_matches,
    }


# ── Economy monitor ───────────────────────────────────────────────────────────

@router.get("/economy", dependencies=[Depends(_check_key)])
async def admin_economy(db: AsyncSession = Depends(get_db)):
    """Economy monitor: průměrný gold/level, top gold holders, celkový gold v oběhu."""
    # Celkový gold v oběhu
    total_gold = (await db.execute(select(func.sum(Character.gold)))).scalar_one() or 0

    # Průměrný gold per level
    level_gold_res = await db.execute(
        select(Character.level, func.avg(Character.gold).label("avg_gold"), func.count().label("cnt"))
        .group_by(Character.level)
        .order_by(Character.level)
    )
    per_level = [
        {"level": row.level, "avg_gold": round(row.avg_gold), "players": row.cnt}
        for row in level_gold_res
    ]

    # Top 10 gold holders
    top_res = await db.execute(
        select(Character).order_by(Character.gold.desc()).limit(10)
    )
    top_holders = [
        {"name": c.name, "cls": c.cls, "level": c.level, "gold": c.gold}
        for c in top_res.scalars().all()
    ]

    # Celkový objem transakcí
    tx_volume = (await db.execute(
        select(func.sum(func.abs(GoldTransaction.amount))).select_from(GoldTransaction)
    )).scalar_one() or 0

    # Počet transakcí dle důvodu
    tx_by_reason_res = await db.execute(
        select(GoldTransaction.reason, func.count().label("cnt"), func.sum(GoldTransaction.amount).label("total"))
        .group_by(GoldTransaction.reason)
        .order_by(func.count().desc())
    )
    tx_by_reason = [
        {"reason": row.reason, "count": row.cnt, "total": row.total or 0}
        for row in tx_by_reason_res
    ]

    return {
        "total_gold_in_circulation": total_gold,
        "total_transaction_volume":  tx_volume,
        "gold_per_level":            per_level,
        "top_gold_holders":          top_holders,
        "transactions_by_reason":    tx_by_reason,
    }


# ── Analytics dashboard ────────────────────────────────────────────────────────

@router.get("/analytics", dependencies=[Depends(_check_key)])
async def admin_analytics(db: AsyncSession = Depends(get_db)):
    """Analytics dashboard: retention, engagement, combat, economy."""
    from datetime import timedelta

    now        = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_14d = now - timedelta(days=14)
    cutoff_7d  = now - timedelta(days=7)

    # ── 1. Registrace za posledních 14 dní ────────────────────────────────────
    reg_res = await db.execute(
        select(func.date(User.created_at).label("day"), func.count().label("cnt"))
        .where(User.created_at >= cutoff_14d)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    registrations_by_day = [{"day": str(r.day), "count": r.cnt} for r in reg_res]

    # ── 2. Level distribuce (buckety) ─────────────────────────────────────────
    levels_res = await db.execute(select(Character.level))
    level_buckets: dict[str, int] = {
        "1-10": 0, "11-20": 0, "21-30": 0, "31-50": 0, "51-100": 0, "100+": 0
    }
    for (lv,) in levels_res:
        if   lv <= 10:  level_buckets["1-10"]   += 1
        elif lv <= 20:  level_buckets["11-20"]  += 1
        elif lv <= 30:  level_buckets["21-30"]  += 1
        elif lv <= 50:  level_buckets["31-50"]  += 1
        elif lv <= 100: level_buckets["51-100"] += 1
        else:           level_buckets["100+"]   += 1

    # ── 3. Třídní distribuce ──────────────────────────────────────────────────
    cls_res = await db.execute(
        select(Character.cls, func.count().label("cnt"))
        .group_by(Character.cls)
        .order_by(func.count().desc())
    )
    class_distribution = [{"cls": r.cls, "count": r.cnt} for r in cls_res]

    # ── 4. Top quest completers ───────────────────────────────────────────────
    top_quest_res = await db.execute(
        select(Character.name, Character.cls, Character.level, Character.quests_completed)
        .order_by(Character.quests_completed.desc())
        .limit(10)
    )
    top_quest_completers = [
        {"name": r.name, "cls": r.cls, "level": r.level, "completed": r.quests_completed or 0}
        for r in top_quest_res
    ]

    total_chars = (await db.execute(select(func.count()).select_from(Character))).scalar_one() or 1
    avg_quests  = (await db.execute(select(func.avg(Character.quests_completed)))).scalar_one() or 0

    churn_res   = await db.execute(
        select(func.count()).select_from(Character)
        .where(Character.quests_completed == 0, Character.level <= 2)
    )
    churn_count = churn_res.scalar_one() or 0

    # ── 5. Arena: zápasy dle dne (posledních 7 dní) ───────────────────────────
    arena_day_res = await db.execute(
        select(func.date(ArenaMatch.played_at).label("day"), func.count().label("cnt"))
        .where(ArenaMatch.played_at >= cutoff_7d)
        .group_by(func.date(ArenaMatch.played_at))
        .order_by(func.date(ArenaMatch.played_at))
    )
    arena_by_day = [{"day": str(r.day), "count": r.cnt} for r in arena_day_res]

    # ── 6. Arena: win rate dle třídy ──────────────────────────────────────────
    # Vítězství jako útočník
    att_wins_res = await db.execute(
        select(Character.cls, func.count().label("wins"))
        .join(ArenaMatch, (ArenaMatch.attacker_id == Character.id) & (ArenaMatch.winner_id == Character.id))
        .group_by(Character.cls)
    )
    att_wins = {r.cls: r.wins for r in att_wins_res}

    # Vítězství jako obránce
    def_wins_res = await db.execute(
        select(Character.cls, func.count().label("wins"))
        .join(ArenaMatch, (ArenaMatch.defender_id == Character.id) & (ArenaMatch.winner_id == Character.id))
        .group_by(Character.cls)
    )
    def_wins = {r.cls: r.wins for r in def_wins_res}

    # Celkové zápasy jako útočník
    att_tot_res = await db.execute(
        select(Character.cls, func.count().label("total"))
        .join(ArenaMatch, ArenaMatch.attacker_id == Character.id)
        .group_by(Character.cls)
    )
    att_total = {r.cls: r.total for r in att_tot_res}

    # Celkové zápasy jako obránce
    def_tot_res = await db.execute(
        select(Character.cls, func.count().label("total"))
        .join(ArenaMatch, ArenaMatch.defender_id == Character.id)
        .group_by(Character.cls)
    )
    def_total = {r.cls: r.total for r in def_tot_res}

    all_cls = set(att_total) | set(def_total)
    class_winrates = []
    for cls in sorted(all_cls):
        wins  = att_wins.get(cls, 0) + def_wins.get(cls, 0)
        total = att_total.get(cls, 0) + def_total.get(cls, 0)
        class_winrates.append({
            "cls": cls,
            "wins": wins,
            "total": total,
            "win_pct": round(wins / total * 100, 1) if total > 0 else 0.0,
        })
    class_winrates.sort(key=lambda x: x["win_pct"], reverse=True)

    # ── 7. Economy: denní gold flow za posledních 7 dní ──────────────────────
    gold_flow_res = await db.execute(
        select(
            func.date(GoldTransaction.timestamp).label("day"),
            func.sum(
                case((GoldTransaction.amount > 0, GoldTransaction.amount), else_=0)
            ).label("income"),
            func.sum(
                case((GoldTransaction.amount < 0, GoldTransaction.amount), else_=0)
            ).label("spending"),
            func.count().label("tx_count"),
        )
        .where(GoldTransaction.timestamp >= cutoff_7d)
        .group_by(func.date(GoldTransaction.timestamp))
        .order_by(func.date(GoldTransaction.timestamp))
    )
    gold_flow_by_day = [
        {
            "day":      str(r.day),
            "income":   int(r.income or 0),
            "spending": int(r.spending or 0),
            "net":      int((r.income or 0) + (r.spending or 0)),
            "tx_count": r.tx_count,
        }
        for r in gold_flow_res
    ]

    return {
        "retention": {
            "registrations_by_day": registrations_by_day,
            "level_distribution":   level_buckets,
            "churn_candidates":     churn_count,
            "churn_rate_pct":       round(churn_count / total_chars * 100, 1),
        },
        "engagement": {
            "class_distribution":    class_distribution,
            "top_quest_completers":  top_quest_completers,
            "avg_quests_per_player": round(float(avg_quests), 1),
        },
        "combat": {
            "arena_matches_by_day": arena_by_day,
            "class_win_rates":      class_winrates,
        },
        "economy": {
            "gold_flow_by_day": gold_flow_by_day,
        },
    }


# ── Content toggle ────────────────────────────────────────────────────────────

@router.get("/quests", dependencies=[Depends(_check_key)])
async def admin_quest_list(db: AsyncSession = Depends(get_db)):
    """Seznam všech questů s příznakem disabled (DB-backed, multi-instance safe)."""
    disabled_ids = await get_disabled_quest_ids(db)
    out = []
    for qdef in QUEST_DEFINITIONS:
        out.append({
            "id":         qdef[0],
            "name":       qdef[1],
            "difficulty": qdef[3],
            "min_level":  qdef[8],
            "icon":       qdef[9],
            "disabled":   qdef[0] in disabled_ids,
        })
    return {"quests": out, "disabled_count": len(disabled_ids)}


@router.post("/quest/disable/{quest_id}", dependencies=[Depends(_check_key)])
async def admin_disable_quest(quest_id: int, db: AsyncSession = Depends(get_db)):
    """Deaktivuje quest v DB (bez restartu, funguje napříč instancemi)."""
    if not any(q[0] == quest_id for q in QUEST_DEFINITIONS):
        raise HTTPException(404, f"Quest ID {quest_id} neexistuje.")
    await disable_quest(quest_id, db)
    disabled_ids = await get_disabled_quest_ids(db)
    return {"message": f"Quest {quest_id} deaktivován.", "disabled": sorted(disabled_ids)}


@router.post("/quest/enable/{quest_id}", dependencies=[Depends(_check_key)])
async def admin_enable_quest(quest_id: int, db: AsyncSession = Depends(get_db)):
    """Znovu aktivuje quest v DB."""
    await enable_quest(quest_id, db)
    disabled_ids = await get_disabled_quest_ids(db)
    return {"message": f"Quest {quest_id} aktivován.", "disabled": sorted(disabled_ids)}


# ── Player actions ─────────────────────────────────────────────────────────────

class GoldActionRequest(BaseModel):
    amount: int       # kladné = přidat, záporné = odebrat
    reason: str = "admin_grant"

class CrystalsActionRequest(BaseModel):
    amount: int       # vždy kladné

class SetLevelRequest(BaseModel):
    level:    int       # cílový level (1–999)
    reset_xp: bool = True  # resetovat XP na 0

class BroadcastRequest(BaseModel):
    title:  str
    body:   str = ""
    target: str = "all"   # "all" nebo username


async def _get_char_by_name(name: str, db: AsyncSession) -> Character:
    res = await db.execute(select(Character).where(Character.name == name))
    char = res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, f"Postava '{name}' nenalezena.")
    return char


@router.post("/player/{name}/gold", dependencies=[Depends(_check_key)])
async def admin_player_gold(
    name: str,
    req: GoldActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin: přidá nebo ubere gold hráči."""
    char = await _get_char_by_name(name, db)

    if req.amount == 0:
        raise HTTPException(400, "Částka nesmí být 0.")
    if req.amount < 0 and char.gold + req.amount < 0:
        raise HTTPException(400, f"Hráč má pouze {char.gold} G — nelze odebrat {abs(req.amount)} G.")

    char.gold += req.amount
    await log_gold(db, char, req.amount, GoldReason.QUEST_REWARD,
                   {"source": "admin", "reason": req.reason})
    await db.commit()

    return {
        "message": f"{'Přidáno' if req.amount > 0 else 'Odebráno'} {abs(req.amount)} G hráči {name}.",
        "gold_after": char.gold,
    }


@router.post("/player/{name}/crystals", dependencies=[Depends(_check_key)])
async def admin_player_crystals(
    name: str,
    req: CrystalsActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin: přidá crystaly hráči."""
    if req.amount <= 0:
        raise HTTPException(400, "Částka musí být kladná.")
    char = await _get_char_by_name(name, db)
    char.crystals = (char.crystals or 0) + req.amount

    from routers.crystals import add_crystals
    await add_crystals(char.id, req.amount, "admin_grant", db)
    await db.commit()

    return {
        "message": f"Přidáno {req.amount} Crystalů hráči {name}.",
        "crystals_after": char.crystals,
    }


@router.post("/player/{name}/reset-quest", dependencies=[Depends(_check_key)])
async def admin_reset_quest(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin: resetuje aktivní quest hráče (bez odměny)."""
    char = await _get_char_by_name(name, db)
    res = await db.execute(select(Quest).where(Quest.character_id == char.id))
    quest = res.scalar_one_or_none()

    if not quest or quest.status == QuestStatus.IDLE:
        raise HTTPException(400, "Hráč nemá aktivní quest.")

    old_status = quest.status
    quest.status     = QuestStatus.IDLE
    quest.quest_def_id = None
    quest.started_at   = None
    quest.finishes_at  = None
    await db.commit()

    return {"message": f"Quest hráče {name} resetován (byl: {old_status})."}


@router.post("/player/{name}/set-level", dependencies=[Depends(_check_key)])
async def admin_set_level(
    name: str,
    req: SetLevelRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin: nastaví level hráče. Přepočítá stats, volitelně resetuje XP."""
    if not (1 <= req.level <= 999):
        raise HTTPException(400, "Level musí být v rozsahu 1–999.")

    char = await _get_char_by_name(name, db)
    old_level = char.level
    char.level = req.level
    if req.reset_xp:
        char.xp = 0

    # Stat body: přidat nebo odebrat podle rozdílu levelů
    level_diff = req.level - old_level
    char.stat_points = max(0, (char.stat_points or 0) + level_diff)
    char.recalculate_stats()

    await db.commit()
    return {
        "message": f"Level hráče {name} změněn: {old_level} → {req.level}.",
        "level":       char.level,
        "stat_points": char.stat_points,
    }


@router.post("/player/{name}/kick-guild", dependencies=[Depends(_check_key)])
async def admin_kick_from_guild(
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin: vyhodí hráče z cechu."""
    char = await _get_char_by_name(name, db)

    if not char.guild_id:
        raise HTTPException(400, f"Hráč {name} není v žádném cechu.")

    guild_id      = char.guild_id
    char.guild_id  = None
    char.guild_role = None
    await db.commit()

    return {"message": f"Hráč {name} byl vyhozen z cechu (guild_id: {guild_id})."}


# ── Content Management API ────────────────────────────────────────────────────

class CreateQuestRequest(BaseModel):
    name:             str
    description:      str = ""
    difficulty:       str = "normal"   # "easy" | "normal" | "hard" | "boss"
    duration_minutes: int = 10
    reward_xp:        int = 100
    reward_gold_min:  int = 50
    reward_gold_max:  int = 100
    min_level:        int = 1
    icon:             str = "⚔️"


@router.post("/quest/create", dependencies=[Depends(_check_key)])
async def admin_create_quest(req: CreateQuestRequest):
    """Admin: přidá nový quest do config/quests.json a hot-reloaduje definice."""
    import json
    from game.config_loader import CONFIG_DIR, load_quest_definitions, reload_config

    valid_difficulties = {"easy", "normal", "hard", "boss"}
    if req.difficulty not in valid_difficulties:
        raise HTTPException(400, f"Neplatná obtížnost. Povolené: {sorted(valid_difficulties)}")
    if req.duration_minutes < 1:
        raise HTTPException(400, "Délka questu musí být alespoň 1 minuta.")
    if req.reward_xp < 0 or req.reward_gold_min < 0 or req.reward_gold_max < 0:
        raise HTTPException(400, "Odměny nesmí být záporné.")
    if req.reward_gold_min > req.reward_gold_max:
        raise HTTPException(400, "reward_gold_min nesmí být větší než reward_gold_max.")
    if req.min_level < 1:
        raise HTTPException(400, "Min. level musí být aspoň 1.")

    quests = load_quest_definitions()
    next_id = max((q[0] for q in quests), default=0) + 1

    # Formát: [id, name, description, difficulty, duration_min, xp, gold_min, gold_max, min_level, icon]
    new_quest = [
        next_id, req.name, req.description, req.difficulty,
        req.duration_minutes, req.reward_xp,
        req.reward_gold_min, req.reward_gold_max,
        req.min_level, req.icon,
    ]
    quests.append(new_quest)

    quest_path = CONFIG_DIR / "quests.json"
    with open(quest_path, "w", encoding="utf-8") as f:
        json.dump(quests, f, ensure_ascii=False, indent=2)

    result = reload_config()
    return {
        "message": f"Quest '{req.name}' (ID {next_id}) vytvořen a načten.",
        "quest_id": next_id,
        "total_quests": result["quest_count"],
    }


@router.post("/config/reload", dependencies=[Depends(_check_key)])
async def admin_reload_config():
    """Admin: znovu načte herní konfiguraci z JSON souborů bez restartu."""
    from game.config_loader import reload_config
    result = reload_config()
    return {"message": "Konfigurace úspěšně načtena.", **result}


# ── Crystal shop slevy ────────────────────────────────────────────────────────

class CreateSaleRequest(BaseModel):
    item_key:        str
    sale_cost:       int
    starts_in_hours: int = 0    # 0 = ihned
    duration_hours:  int = 24
    label:           str | None = None   # "Black Friday", "Vánoce" apod.


@router.get("/crystal-shop-items", dependencies=[Depends(_check_key)])
async def admin_crystal_shop_items():
    """Admin: seznam položek v Crystal shopu (pro select ve formuláři)."""
    return {
        "items": [
            {"key": k, "name": v["name"], "emoji": v["emoji"], "cost": v["cost"], "type": v["type"]}
            for k, v in CRYSTAL_SHOP.items()
        ]
    }


@router.get("/crystal-sales", dependencies=[Depends(_check_key)])
async def admin_list_crystal_sales(db: AsyncSession = Depends(get_db)):
    """Admin: seznam všech naplánovaných a aktivních Crystal shop slev."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    res = await db.execute(
        select(ScheduledCrystalSale).order_by(ScheduledCrystalSale.ends_at.desc()).limit(50)
    )
    sales = res.scalars().all()
    return {
        "sales": [s.to_dict(now) for s in sales],
        "active_count": sum(1 for s in sales if s.is_currently_active(now)),
    }


@router.post("/crystal-sale", dependencies=[Depends(_check_key)])
async def admin_create_crystal_sale(req: CreateSaleRequest, db: AsyncSession = Depends(get_db)):
    """Admin: naplánuje slevovou akci na položku v Crystal shopu."""
    from datetime import timedelta

    item_def = CRYSTAL_SHOP.get(req.item_key)
    if not item_def:
        raise HTTPException(404, f"Položka '{req.item_key}' v Crystal shopu neexistuje.")
    if req.sale_cost <= 0:
        raise HTTPException(400, "Slevová cena musí být kladná.")
    if req.sale_cost >= item_def["cost"]:
        raise HTTPException(
            400,
            f"Slevová cena ({req.sale_cost}) musí být nižší než originální ({item_def['cost']}) 💎.",
        )
    if req.duration_hours < 1:
        raise HTTPException(400, "Délka akce musí být aspoň 1 hodina.")

    now       = datetime.now(timezone.utc).replace(tzinfo=None)
    starts_at = now + timedelta(hours=req.starts_in_hours)
    ends_at   = starts_at + timedelta(hours=req.duration_hours)

    sale = ScheduledCrystalSale(
        item_key=req.item_key,
        original_cost=item_def["cost"],
        sale_cost=req.sale_cost,
        starts_at=starts_at,
        ends_at=ends_at,
        label=req.label,
    )
    db.add(sale)
    await db.commit()

    start_msg = "ihned" if req.starts_in_hours == 0 else f"za {req.starts_in_hours}h"
    disc_pct  = round((1 - req.sale_cost / item_def["cost"]) * 100)
    return {
        "message": (
            f"Sleva -{disc_pct}% na '{item_def['name']}' naplánována "
            f"({start_msg}, trvá {req.duration_hours}h). "
            f"{item_def['cost']} 💎 → {req.sale_cost} 💎"
        ),
        "sale": sale.to_dict(now),
    }


@router.delete("/crystal-sale/{sale_id}", dependencies=[Depends(_check_key)])
async def admin_cancel_crystal_sale(sale_id: int, db: AsyncSession = Depends(get_db)):
    """Admin: zruší (smaže) naplánovanou slevu."""
    res  = await db.execute(select(ScheduledCrystalSale).where(ScheduledCrystalSale.id == sale_id))
    sale = res.scalar_one_or_none()
    if not sale:
        raise HTTPException(404, f"Sleva ID {sale_id} nenalezena.")
    await db.delete(sale)
    await db.commit()
    return {"message": f"Sleva ID {sale_id} zrušena."}


# ── World Events admin ─────────────────────────────────────────────────────────

@router.get("/world-event", dependencies=[Depends(_check_key)])
async def admin_world_event(db: AsyncSession = Depends(get_db)):
    """Aktuální World Event + statistiky přispěvatelů."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    res = await db.execute(
        select(WorldEvent).where(WorldEvent.is_active == True, WorldEvent.ends_at > now)
        .order_by(WorldEvent.id.desc()).limit(1)
    )
    event = res.scalar_one_or_none()

    # Poslední 3 eventy v historii
    hist_res = await db.execute(
        select(WorldEvent).order_by(WorldEvent.id.desc()).limit(5)
    )
    history = hist_res.scalars().all()

    if not event:
        return {
            "event": None,
            "contributors": 0,
            "top_contributors": [],
            "history": [e.to_dict() for e in history],
            "definitions": [{"name": d["name"], "event_type": d["event_type"], "goal": d["goal"]} for d in WORLD_EVENT_DEFINITIONS],
        }

    # Top přispěvatelé
    top_res = await db.execute(
        select(WorldEventContrib, Character.name)
        .join(Character, Character.id == WorldEventContrib.character_id)
        .where(WorldEventContrib.event_id == event.id)
        .order_by(WorldEventContrib.contribution.desc())
        .limit(15)
    )
    top_rows = top_res.all()
    contrib_count = (await db.execute(
        select(func.count()).where(WorldEventContrib.event_id == event.id)
    )).scalar() or 0

    return {
        "event": event.to_dict(),
        "contributors": contrib_count,
        "top_contributors": [{"name": name, "contribution": c.contribution} for c, name in top_rows],
        "history": [e.to_dict() for e in history],
        "definitions": [{"name": d["name"], "event_type": d["event_type"], "goal": d["goal"]} for d in WORLD_EVENT_DEFINITIONS],
    }


@router.post("/world-event/complete", dependencies=[Depends(_check_key)])
async def admin_complete_world_event(db: AsyncSession = Depends(get_db)):
    """Admin: force-completes aktuální World Event."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    res = await db.execute(
        select(WorldEvent).where(WorldEvent.is_active == True, WorldEvent.ends_at > now)
        .order_by(WorldEvent.id.desc()).limit(1)
    )
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(404, "Žádný aktivní World Event.")
    if event.is_completed:
        raise HTTPException(400, "Event je již dokončen.")

    event.is_completed     = True
    event.current_progress = event.goal
    await db.commit()

    return {"message": f"Event '{event.name}' označen jako dokončený.", "event": event.to_dict()}


class NewEventRequest(BaseModel):
    definition_index: int = 0   # index v WORLD_EVENT_DEFINITIONS (0,1,2)
    duration_days:    int = 7


@router.post("/world-event/new", dependencies=[Depends(_check_key)])
async def admin_new_world_event(req: NewEventRequest, db: AsyncSession = Depends(get_db)):
    """Admin: deaktivuje stávající event a vytvoří nový."""
    from datetime import timedelta

    # Deaktivuj stávající
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_res = await db.execute(
        select(WorldEvent).where(WorldEvent.is_active == True, WorldEvent.ends_at > now)
    )
    for old in old_res.scalars().all():
        old.is_active = False

    idx  = max(0, min(req.definition_index, len(WORLD_EVENT_DEFINITIONS) - 1))
    defn = WORLD_EVENT_DEFINITIONS[idx]

    event = WorldEvent(
        name=defn["name"],
        description=defn["description"],
        event_type=defn["event_type"],
        goal=defn["goal"],
        current_progress=0,
        starts_at=now,
        ends_at=now + timedelta(days=req.duration_days),
        is_active=True,
        is_completed=False,
        reward_gold=defn["reward_gold"],
        reward_crystals=defn["reward_crystals"],
        reward_title=defn.get("reward_title"),
    )
    db.add(event)
    await db.commit()

    return {"message": f"Nový event '{event.name}' spuštěn.", "event": event.to_dict()}


class ScheduleEventRequest(BaseModel):
    name:             str
    description:      str = ""
    event_type:       str           # "quests" | "dungeon_clears" | "boss_damage" | "kills"
    goal:             int
    reward_gold:      int = 1000
    reward_crystals:  int = 50
    reward_title:     str | None = None
    starts_in_hours:  int = 0       # 0 = ihned
    duration_days:    int = 7


@router.post("/world-event/schedule", dependencies=[Depends(_check_key)])
async def admin_schedule_world_event(req: ScheduleEventRequest, db: AsyncSession = Depends(get_db)):
    """Admin: naplánuje vlastní World Event s libovolnými parametry."""
    from datetime import timedelta
    from models.world_event import EVENT_TYPE_LABELS

    if req.event_type not in EVENT_TYPE_LABELS:
        raise HTTPException(400, f"Neplatný typ. Povolené: {list(EVENT_TYPE_LABELS.keys())}")
    if req.goal <= 0:
        raise HTTPException(400, "Cíl musí být kladné číslo.")
    if req.duration_days < 1:
        raise HTTPException(400, "Délka musí být aspoň 1 den.")

    now       = datetime.now(timezone.utc).replace(tzinfo=None)
    starts_at = now + timedelta(hours=req.starts_in_hours)
    ends_at   = starts_at + timedelta(days=req.duration_days)

    # Pokud event začíná ihned, deaktivuj předchozí
    if req.starts_in_hours == 0:
        old_res = await db.execute(
            select(WorldEvent).where(WorldEvent.is_active == True, WorldEvent.ends_at > now)
        )
        for old in old_res.scalars().all():
            old.is_active = False

    event = WorldEvent(
        name=req.name,
        description=req.description,
        event_type=req.event_type,
        goal=req.goal,
        current_progress=0,
        starts_at=starts_at,
        ends_at=ends_at,
        is_active=(req.starts_in_hours == 0),
        is_completed=False,
        reward_gold=req.reward_gold,
        reward_crystals=req.reward_crystals,
        reward_title=req.reward_title,
    )
    db.add(event)
    await db.commit()

    start_msg = "ihned" if req.starts_in_hours == 0 else f"za {req.starts_in_hours}h"
    return {
        "message": f"Event '{req.name}' naplánován ({start_msg}, trvá {req.duration_days} dní).",
        "event": event.to_dict(),
    }


# ── World Boss admin ───────────────────────────────────────────────────────────

@router.get("/boss", dependencies=[Depends(_check_key)])
async def admin_boss_info(db: AsyncSession = Depends(get_db)):
    """Admin: info o aktivním World Bossovi + participanti + definice bossů."""
    res = await db.execute(
        select(WorldBoss).where(WorldBoss.is_alive == True).order_by(WorldBoss.id.desc()).limit(1)
    )
    boss = res.scalar_one_or_none()

    parts_data = []
    if boss:
        parts_res = await db.execute(
            select(BossParticipation, Character.name, Character.cls)
            .join(Character, Character.id == BossParticipation.character_id)
            .where(BossParticipation.boss_id == boss.id)
            .order_by(BossParticipation.total_damage.desc())
        )
        total_dmg = 0
        rows = parts_res.all()
        total_dmg = sum(r[0].total_damage for r in rows) or 1
        parts_data = [
            {
                "name":    r[1],
                "cls":     r[2],
                "damage":  r[0].total_damage,
                "attacks": r[0].attacks_count,
                "pct":     round(r[0].total_damage / total_dmg * 100, 1),
            }
            for r in rows
        ]

    # Poslední 3 mrtví bossové
    dead_res = await db.execute(
        select(WorldBoss).where(WorldBoss.is_alive == False)
        .order_by(WorldBoss.killed_at.desc()).limit(3)
    )

    return {
        "active_boss":   boss.to_dict() if boss else None,
        "participants":  parts_data,
        "recent_bosses": [b.to_dict() for b in dead_res.scalars().all()],
        "boss_definitions": [
            {"key": k, "name": v["name"], "emoji": v["emoji"],
             "hp_base": v["hp_base"], "min_level": v["min_level"]}
            for k, v in WORLD_BOSS_DEFINITIONS.items()
        ],
    }


class AdminSpawnBossRequest(BaseModel):
    boss_key:     str
    player_count: int = 10


@router.post("/boss/spawn", dependencies=[Depends(_check_key)])
async def admin_spawn_boss(req: AdminSpawnBossRequest, db: AsyncSession = Depends(get_db)):
    """Admin: spawne nového World Bosse (přes existující boss spawn logiku)."""
    from routers.boss import spawn_boss, SpawnBossRequest
    return await spawn_boss(SpawnBossRequest(boss_key=req.boss_key, player_count=req.player_count), db)


# ── Broadcast notifikace ───────────────────────────────────────────────────────

@router.post("/broadcast", dependencies=[Depends(_check_key)])
async def admin_broadcast(req: BroadcastRequest, db: AsyncSession = Depends(get_db)):
    """Admin: pošle systémovou notifikaci všem hráčům nebo konkrétnímu hráči."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if req.target == "all":
        chars_res = await db.execute(select(Character))
        chars = chars_res.scalars().all()
    else:
        # Najdi podle username nebo character name
        user_res = await db.execute(select(User).where(User.username == req.target))
        user = user_res.scalar_one_or_none()
        if user:
            char_res = await db.execute(select(Character).where(Character.user_id == user.id))
            char = char_res.scalar_one_or_none()
            chars = [char] if char else []
        else:
            char_res = await db.execute(select(Character).where(Character.name == req.target))
            char = char_res.scalar_one_or_none()
            chars = [char] if char else []

        if not chars:
            raise HTTPException(404, f"Hráč '{req.target}' nenalezen.")

    count = 0
    for char in chars:
        notif = Notification(
            character_id=char.id,
            type=NotifType.SYSTEM,
            title=req.title,
            body=req.body,
            is_read=False,
            created_at=now,
        )
        db.add(notif)
        count += 1

    await db.commit()
    return {
        "message": f"Notifikace odeslána {count} hráčům.",
        "recipient_count": count,
        "target": req.target,
    }


# ── A/B Experiments ───────────────────────────────────────────────────────────

class CreateExperimentRequest(BaseModel):
    name:        str
    description: str = ""
    group_start: int = 0    # 0–9
    group_end:   int = 4    # 0–9, musí být >= group_start
    overrides:   dict = {}  # {"ability_trigger_prob": 0.30, "gold_reward_win": 1.5}


class UpdateExperimentRequest(BaseModel):
    name:        str | None = None
    description: str | None = None
    group_start: int | None = None
    group_end:   int | None = None
    overrides:   dict | None = None


class BugStatusUpdate(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"]

class BugNoteUpdate(BaseModel):
    admin_note: str


@router.get("/experiments", dependencies=[Depends(_check_key)])
async def admin_list_experiments(db: AsyncSession = Depends(get_db)):
    """Admin: seznam všech A/B experimentů + přehled overridovatelných parametrů."""
    res = await db.execute(select(Experiment).order_by(Experiment.id.desc()))
    experiments = res.scalars().all()

    return {
        "experiments":          [e.to_dict() for e in experiments],
        "overridable_params":   OVERRIDABLE_PARAMS,
        "total_groups":         10,
        "group_distribution":   "0–9, přiřazeno náhodně při vytvoření postavy",
    }


@router.post("/experiment", dependencies=[Depends(_check_key)])
async def admin_create_experiment(req: CreateExperimentRequest, db: AsyncSession = Depends(get_db)):
    """Admin: vytvoří nový A/B experiment."""
    if not (0 <= req.group_start <= 9) or not (0 <= req.group_end <= 9):
        raise HTTPException(400, "Skupiny musí být v rozsahu 0–9.")
    if req.group_start > req.group_end:
        raise HTTPException(400, "group_start nesmí být větší než group_end.")

    invalid_keys = [k for k in req.overrides if k not in OVERRIDABLE_PARAMS]
    if invalid_keys:
        raise HTTPException(400, f"Neznámé override klíče: {invalid_keys}. Povolené: {list(OVERRIDABLE_PARAMS.keys())}")

    # Validuj hodnoty dle range
    for k, v in req.overrides.items():
        param = OVERRIDABLE_PARAMS[k]
        lo, hi = param["range"]
        if not (lo <= float(v) <= hi):
            raise HTTPException(400, f"Hodnota '{k}' ({v}) mimo povolený rozsah [{lo}, {hi}].")

    exp = Experiment(
        name=req.name,
        description=req.description,
        group_start=req.group_start,
        group_end=req.group_end,
        is_active=True,
    )
    exp.set_overrides(req.overrides)
    db.add(exp)
    await db.commit()
    await db.refresh(exp)
    invalidate_experiment_cache()

    groups_covered = list(range(req.group_start, req.group_end + 1))
    pct = round(len(groups_covered) / 10 * 100)
    return {
        "message": (
            f"Experiment '{req.name}' vytvořen. "
            f"Skupiny {req.group_start}–{req.group_end} ({pct}% hráčů)."
        ),
        "experiment": exp.to_dict(),
    }


@router.put("/experiment/{exp_id}", dependencies=[Depends(_check_key)])
async def admin_update_experiment(
    exp_id: int,
    req: UpdateExperimentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin: upraví experiment (název, skupiny, override hodnoty)."""
    res = await db.execute(select(Experiment).where(Experiment.id == exp_id))
    exp = res.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, f"Experiment ID {exp_id} nenalezen.")

    if req.name        is not None: exp.name        = req.name
    if req.description is not None: exp.description = req.description
    if req.group_start is not None: exp.group_start  = req.group_start
    if req.group_end   is not None: exp.group_end    = req.group_end
    if req.overrides   is not None:
        invalid_keys = [k for k in req.overrides if k not in OVERRIDABLE_PARAMS]
        if invalid_keys:
            raise HTTPException(400, f"Neznámé override klíče: {invalid_keys}.")
        exp.set_overrides(req.overrides)

    if exp.group_start > exp.group_end:
        raise HTTPException(400, "group_start nesmí být větší než group_end.")

    await db.commit()
    invalidate_experiment_cache()
    return {"message": f"Experiment '{exp.name}' aktualizován.", "experiment": exp.to_dict()}


@router.post("/experiment/{exp_id}/toggle", dependencies=[Depends(_check_key)])
async def admin_toggle_experiment(exp_id: int, db: AsyncSession = Depends(get_db)):
    """Admin: aktivuje / deaktivuje experiment."""
    res = await db.execute(select(Experiment).where(Experiment.id == exp_id))
    exp = res.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, f"Experiment ID {exp_id} nenalezen.")

    exp.is_active = not exp.is_active
    await db.commit()
    invalidate_experiment_cache()
    state = "aktivován" if exp.is_active else "deaktivován"
    return {"message": f"Experiment '{exp.name}' {state}.", "is_active": exp.is_active}


@router.delete("/experiment/{exp_id}", dependencies=[Depends(_check_key)])
async def admin_delete_experiment(exp_id: int, db: AsyncSession = Depends(get_db)):
    """Admin: smaže experiment."""
    res = await db.execute(select(Experiment).where(Experiment.id == exp_id))
    exp = res.scalar_one_or_none()
    if not exp:
        raise HTTPException(404, f"Experiment ID {exp_id} nenalezen.")
    await db.delete(exp)
    await db.commit()
    invalidate_experiment_cache()
    return {"message": f"Experiment '{exp.name}' smazán."}


@router.get("/experiments/analytics", dependencies=[Depends(_check_key)])
async def admin_experiment_analytics(db: AsyncSession = Depends(get_db)):
    """
    Admin: klíčové metriky rozdělené dle experiment_group (0–9).
    Umožňuje porovnat výkon skupin a detekovat vliv balance změn.
    """
    # Počet hráčů per skupina
    group_counts_res = await db.execute(
        select(Character.experiment_group, func.count().label("players"))
        .group_by(Character.experiment_group)
        .order_by(Character.experiment_group)
    )
    group_players = {row.experiment_group: row.players for row in group_counts_res}

    # Průměrný level per skupina
    group_level_res = await db.execute(
        select(Character.experiment_group, func.avg(Character.level).label("avg_level"))
        .group_by(Character.experiment_group)
        .order_by(Character.experiment_group)
    )
    group_level = {row.experiment_group: round(float(row.avg_level or 1), 1) for row in group_level_res}

    # Průměrné gold per skupina
    group_gold_res = await db.execute(
        select(Character.experiment_group, func.avg(Character.gold).label("avg_gold"))
        .group_by(Character.experiment_group)
        .order_by(Character.experiment_group)
    )
    group_gold = {row.experiment_group: round(float(row.avg_gold or 0)) for row in group_gold_res}

    # Win rate v arénách per skupina (jako útočník)
    att_wins_res = await db.execute(
        select(Character.experiment_group, func.count().label("wins"))
        .join(ArenaMatch, (ArenaMatch.attacker_id == Character.id) & (ArenaMatch.winner_id == Character.id))
        .group_by(Character.experiment_group)
    )
    group_att_wins = {row.experiment_group: row.wins for row in att_wins_res}

    att_total_res = await db.execute(
        select(Character.experiment_group, func.count().label("total"))
        .join(ArenaMatch, ArenaMatch.attacker_id == Character.id)
        .group_by(Character.experiment_group)
    )
    group_att_total = {row.experiment_group: row.total for row in att_total_res}

    # Průměrný počet splněných questů per skupina
    quest_res = await db.execute(
        select(Character.experiment_group, func.avg(Character.quests_completed).label("avg_quests"))
        .group_by(Character.experiment_group)
        .order_by(Character.experiment_group)
    )
    group_quests = {row.experiment_group: round(float(row.avg_quests or 0), 1) for row in quest_res}

    # Sestavení výsledku
    groups_out = []
    for g in range(10):
        wins  = group_att_wins.get(g, 0)
        total = group_att_total.get(g, 0)
        groups_out.append({
            "group":        g,
            "players":      group_players.get(g, 0),
            "avg_level":    group_level.get(g, 1.0),
            "avg_gold":     group_gold.get(g, 0),
            "arena_win_pct": round(wins / total * 100, 1) if total > 0 else None,
            "arena_matches": total,
            "avg_quests_completed": group_quests.get(g, 0.0),
        })

    # Aktivní experimenty pro přiřazení skupin
    exp_res = await db.execute(select(Experiment).where(Experiment.is_active == True).order_by(Experiment.id))
    active_experiments = [e.to_dict() for e in exp_res.scalars().all()]

    return {
        "groups":              groups_out,
        "active_experiments":  active_experiments,
        "note":                "Skupiny bez experimentu používají defaultní hodnoty.",
    }


# ── Crystal economy analytics ─────────────────────────────────────────────────

@router.get("/crystals/analytics", dependencies=[Depends(_check_key)])
async def admin_crystal_analytics(db: AsyncSession = Depends(get_db)):
    """
    Crystal economy analytics — přehled earned vs spent, distribuce zdrojů,
    top earneři/spenderé, denní aktivita (14 dní).
    """
    from models.crystal import CrystalTransaction
    from sqlalchemy import cast, Date
    from datetime import timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Celkové součty
    totals_res = await db.execute(
        select(
            func.sum(case((CrystalTransaction.amount > 0, CrystalTransaction.amount), else_=0)),
            func.sum(case((CrystalTransaction.amount < 0, CrystalTransaction.amount), else_=0)),
            func.count(),
        ).select_from(CrystalTransaction)
    )
    total_earned, total_spent, total_txns = totals_res.one()

    # Celkový oběh (sum crystalů u všech postav)
    circulation_res = await db.execute(
        select(func.sum(Character.crystals)).select_from(Character)
    )
    total_circulation = circulation_res.scalar_one() or 0

    # Earning breakdown dle prefixu reason (posledních 30 dní)
    thirty_ago = now - timedelta(days=30)
    breakdown_res = await db.execute(
        select(
            CrystalTransaction.reason,
            func.sum(CrystalTransaction.amount).label("total"),
            func.count().label("count"),
        )
        .where(
            CrystalTransaction.amount > 0,
            CrystalTransaction.timestamp >= thirty_ago,
        )
        .group_by(CrystalTransaction.reason)
        .order_by(func.sum(CrystalTransaction.amount).desc())
        .limit(30)
    )
    breakdown = [
        {"reason": row[0], "total": int(row[1]), "count": int(row[2])}
        for row in breakdown_res.all()
    ]

    # Top earneři (all time)
    top_earners_res = await db.execute(
        select(Character.name, func.sum(CrystalTransaction.amount).label("earned"))
        .join(CrystalTransaction, CrystalTransaction.character_id == Character.id)
        .where(CrystalTransaction.amount > 0)
        .group_by(Character.id, Character.name)
        .order_by(func.sum(CrystalTransaction.amount).desc())
        .limit(5)
    )
    top_earners = [{"name": row[0], "earned": int(row[1])} for row in top_earners_res.all()]

    # Top spenderé (all time)
    top_spenders_res = await db.execute(
        select(Character.name, func.sum(CrystalTransaction.amount).label("spent"))
        .join(CrystalTransaction, CrystalTransaction.character_id == Character.id)
        .where(CrystalTransaction.amount < 0)
        .group_by(Character.id, Character.name)
        .order_by(func.sum(CrystalTransaction.amount).asc())
        .limit(5)
    )
    top_spenders = [{"name": row[0], "spent": abs(int(row[1]))} for row in top_spenders_res.all()]

    # Denní earned crystaly (posledních 14 dní)
    daily_res = await db.execute(
        select(
            cast(CrystalTransaction.timestamp, Date).label("day"),
            func.sum(CrystalTransaction.amount).label("earned"),
        )
        .where(
            CrystalTransaction.amount > 0,
            CrystalTransaction.timestamp >= now - timedelta(days=14),
        )
        .group_by(cast(CrystalTransaction.timestamp, Date))
        .order_by(cast(CrystalTransaction.timestamp, Date))
    )
    daily = [{"day": str(row[0]), "earned": int(row[1])} for row in daily_res.all()]

    # Průměrné crystaly na hráče
    avg_crystals_res = await db.execute(
        select(func.avg(Character.crystals)).select_from(Character)
    )
    avg_crystals = round(float(avg_crystals_res.scalar_one() or 0), 1)

    # Počet hráčů s 0 crystaly (nikdy nevydělali nebo všechno utratili)
    zero_res = await db.execute(
        select(func.count()).select_from(Character).where(
            (Character.crystals == None) | (Character.crystals == 0)
        )
    )
    zero_count = zero_res.scalar_one() or 0

    return {
        "summary": {
            "total_earned":      int(total_earned or 0),
            "total_spent":       abs(int(total_spent or 0)),
            "total_transactions": int(total_txns or 0),
            "net_circulation":   int(total_circulation),
            "avg_crystals_per_player": avg_crystals,
            "players_with_zero": zero_count,
        },
        "breakdown_30d":  breakdown,
        "top_earners":    top_earners,
        "top_spenders":   top_spenders,
        "daily_14d":      daily,
    }


# ── Advanced analytics ─────────────────────────────────────────────────────────

@router.get("/analytics/advanced", dependencies=[Depends(_check_key)])
async def admin_analytics_advanced(db: AsyncSession = Depends(get_db)):
    """
    Advanced analytics: funnel analýza, class vs class matchupy,
    denní aktivní uživatelé (DAU), economy health (velocity, sink ratio, Gini).
    """
    from datetime import timedelta

    now        = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_14d = now - timedelta(days=14)
    cutoff_7d  = now - timedelta(days=7)

    # ── 1. Funnel analýza ─────────────────────────────────────────────────────
    total = (await db.execute(select(func.count()).select_from(Character))).scalar_one() or 1

    has_quest = (await db.execute(
        select(func.count()).select_from(Character).where(Character.quests_completed >= 1)
    )).scalar_one()

    # Hráči s alespoň 1 arena zápasem (útočník nebo obránce)
    arena_chars_sq = union(
        select(ArenaMatch.attacker_id.label("cid")),
        select(ArenaMatch.defender_id.label("cid")),
    ).subquery()
    has_arena = (await db.execute(
        select(func.count()).select_from(arena_chars_sq)
    )).scalar_one()

    has_guild = (await db.execute(
        select(func.count()).select_from(Character).where(Character.guild_id.isnot(None))
    )).scalar_one()

    level_20 = (await db.execute(
        select(func.count()).select_from(Character).where(Character.level >= 20)
    )).scalar_one()

    funnel = {
        "total":        total,
        "first_quest":  has_quest,
        "first_arena":  has_arena,
        "joined_guild": has_guild,
        "level_20":     level_20,
    }

    # ── 2. Class vs class matchupy ─────────────────────────────────────────────
    Attacker = aliased(Character, flat=True)
    Defender = aliased(Character, flat=True)

    matchup_res = await db.execute(
        select(
            Attacker.cls.label("att_cls"),
            Defender.cls.label("def_cls"),
            func.count().label("total"),
            func.sum(
                case((ArenaMatch.winner_id == ArenaMatch.attacker_id, 1), else_=0)
            ).label("att_wins"),
        )
        .join(Attacker, ArenaMatch.attacker_id == Attacker.id)
        .join(Defender, ArenaMatch.defender_id == Defender.id)
        .group_by(Attacker.cls, Defender.cls)
    )
    matchups = []
    for row in matchup_res:
        total_m = row.total or 0
        matchups.append({
            "attacker_cls":      row.att_cls,
            "defender_cls":      row.def_cls,
            "total":             total_m,
            "attacker_wins":     row.att_wins or 0,
            "attacker_win_pct":  round((row.att_wins or 0) / total_m * 100, 1) if total_m > 0 else 0.0,
        })

    # ── 3. Daily Active Users — počet unikátních hráčů s aktivitou dle dne ───
    dau_res = await db.execute(
        select(
            func.date(GoldTransaction.timestamp).label("day"),
            func.count(func.distinct(GoldTransaction.character_id)).label("dau"),
        )
        .where(GoldTransaction.timestamp >= cutoff_14d)
        .group_by(func.date(GoldTransaction.timestamp))
        .order_by(func.date(GoldTransaction.timestamp))
    )
    daily_active_users = [{"day": str(r.day), "dau": r.dau} for r in dau_res]

    # ── 4. Economy health ──────────────────────────────────────────────────────
    gold_7d_res = await db.execute(
        select(
            func.sum(
                case((GoldTransaction.amount > 0, GoldTransaction.amount), else_=0)
            ).label("income"),
            func.sum(
                case((GoldTransaction.amount < 0, GoldTransaction.amount), else_=0)
            ).label("spending"),
        )
        .where(GoldTransaction.timestamp >= cutoff_7d)
    )
    row_7d      = gold_7d_res.one()
    income_7d   = int(row_7d.income or 0)
    spending_7d = abs(int(row_7d.spending or 0))
    net_7d      = income_7d - spending_7d

    sink_source_ratio  = round(spending_7d / income_7d, 3) if income_7d > 0 else 0.0
    avg_daily_velocity = round((income_7d + spending_7d) / 7)
    if net_7d > income_7d * 0.1:
        trend = "inflating"
    elif net_7d < -income_7d * 0.1:
        trend = "deflating"
    else:
        trend = "balanced"

    # Gini koeficient distribuce goldu (0 = rovnoměrnost, 1 = extrémní nerovnost)
    gold_vals_res = await db.execute(
        select(Character.gold).where(Character.gold > 0).order_by(Character.gold)
    )
    gold_vals = [r[0] for r in gold_vals_res]
    gini = 0.0
    if len(gold_vals) > 1:
        n          = len(gold_vals)
        total_gold = sum(gold_vals)
        numerator  = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(gold_vals))
        gini = round(numerator / (n * total_gold), 3) if total_gold > 0 else 0.0

    return {
        "funnel":             funnel,
        "combat_matchups":    matchups,
        "daily_active_users": daily_active_users,
        "economy_health": {
            "income_7d":          income_7d,
            "spending_7d":        spending_7d,
            "net_7d":             net_7d,
            "sink_source_ratio":  sink_source_ratio,
            "avg_daily_velocity": avg_daily_velocity,
            "trend":              trend,
            "gini_coefficient":   gini,
        },
    }


# ── Balance alerts ─────────────────────────────────────────────────────────────

@router.get("/alerts", dependencies=[Depends(_check_key)])
async def admin_alerts(
    include_resolved: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Vrátí aktuální balance anomálie. Ve výchozím stavu jen neresolved."""
    q = select(BalanceAlert).order_by(BalanceAlert.detected_at.desc())
    if not include_resolved:
        q = q.where(BalanceAlert.resolved == False)
    result = await db.execute(q)
    alerts = result.scalars().all()
    return {
        "alerts":        [a.to_dict() for a in alerts],
        "total":         len(alerts),
        "unresolved":    sum(1 for a in alerts if not a.resolved),
    }


@router.post("/alerts/{alert_id}/resolve", dependencies=[Depends(_check_key)])
async def admin_resolve_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Označí alert jako resolved (admin potvrdil, že byl řešen)."""
    alert = (await db.execute(select(BalanceAlert).where(BalanceAlert.id == alert_id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(404, f"Alert ID {alert_id} nenalezen.")
    if alert.resolved:
        raise HTTPException(400, "Alert je již resolved.")
    from datetime import datetime, timezone
    alert.resolved    = True
    alert.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"message": f"Alert #{alert_id} označen jako resolved.", "alert": alert.to_dict()}


@router.post("/alerts/run-check", dependencies=[Depends(_check_key)])
async def admin_run_balance_check(db: AsyncSession = Depends(get_db)):
    """Manuálně spustí balance check (bez ohledu na cron lock)."""
    from models.balance_alert import BalanceAlert as BA
    from tasks.balance_monitor import (
        _check_arena_winrate, _check_gold_monopoly,
        _check_gold_farm, _check_season_skew,
    )
    new_alerts: list[str] = []
    for check in [_check_arena_winrate, _check_gold_monopoly, _check_gold_farm, _check_season_skew]:
        try:
            new_alerts += await check(db)
        except Exception as e:
            new_alerts.append(f"ERROR:{check.__name__}:{e}")
    if new_alerts:
        await db.commit()
    return {"message": "Balance check dokončen.", "new_alerts": new_alerts, "count": len(new_alerts)}


# ── BUG REPORTS ──────────────────────────────────────────────────────────────

@router.get("/bugs")
async def admin_list_bugs(
    status: str | None = None,
    severity: str | None = None,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    q = select(BugReport).order_by(BugReport.created_at.desc())
    if status:
        q = q.where(BugReport.status == status)
    if severity:
        q = q.where(BugReport.severity == severity)
    reports = (await db.execute(q)).scalars().all()
    return [r.to_dict() for r in reports]


@router.get("/bugs/{report_id}")
async def admin_get_bug(
    report_id: int,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    return report.to_dict()


@router.patch("/bugs/{report_id}/status")
async def admin_update_bug_status(
    report_id: int,
    payload: BugStatusUpdate,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    report.status = payload.status
    report.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"ok": True}


@router.patch("/bugs/{report_id}/note")
async def admin_update_bug_note(
    report_id: int,
    payload: BugNoteUpdate,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    report.admin_note = payload.admin_note
    report.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"ok": True}


@router.delete("/bugs/{report_id}")
async def admin_delete_bug(
    report_id: int,
    _: str = Depends(_check_key),
    db: AsyncSession = Depends(get_db),
):
    report = (await db.execute(
        select(BugReport).where(BugReport.id == report_id)
    )).scalars().first()
    if not report:
        raise HTTPException(404, "Report nenalezen.")
    await db.delete(report)
    await db.commit()
    return {"ok": True}
