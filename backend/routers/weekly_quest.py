"""
routers/weekly_quest.py — Individuální Weekly Quest Board

Endpointy:
- GET  /weekly-quests/          — vrátí board pro aktuální týden
- POST /weekly-quests/claim/{slot} — nárokuje odměnu za splněný quest
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.user import User
from models.character import Character, xp_to_next
from models.economy import log_gold, GoldReason
from models.weekly_quest import (
    WeeklyQuestProgress, WEEKLY_BOARD_SIZE,
    _week_start_for, _get_week_pool,
)
from routers.auth import get_current_user
from routers.character import char_dict_with_equipment

router = APIRouter(prefix="/weekly-quests", tags=["weekly-quests"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _ensure_board(
    character_id: int,
    week_start: datetime,
    db: AsyncSession,
) -> list[WeeklyQuestProgress]:
    """Vrátí 4 weekly questy pro hráče; pokud neexistují, vytvoří je."""
    res = await db.execute(
        select(WeeklyQuestProgress)
        .where(
            WeeklyQuestProgress.character_id == character_id,
            WeeklyQuestProgress.week_start   == week_start,
        )
        .order_by(WeeklyQuestProgress.slot)
    )
    board = list(res.scalars().all())
    if not board:
        pool = _get_week_pool(week_start)
        board = []
        for slot, entry in enumerate(pool):
            wq = WeeklyQuestProgress(
                character_id=character_id,
                week_start=week_start,
                slot=slot,
                goal_type=entry["goal_type"],
                goal_target=entry["goal_target"],
                reward_xp=entry["reward_xp"],
                reward_gold=entry["reward_gold"],
            )
            db.add(wq)
            board.append(wq)
        await db.flush()
    return board


async def increment_weekly_board(
    character_id: int,
    goal_type: str,
    amount: int,
    db: AsyncSession,
) -> list[dict]:
    """
    Inkrementuje progress weekly board questů daného typu.
    Voláno z quest.py, arena.py, dungeon.py.
    Vrací list nově splněných questů (dict) pro frontend toast.
    """
    if amount <= 0:
        return []

    now        = datetime.now(timezone.utc).replace(tzinfo=None)
    week_start = _week_start_for(now)
    board      = await _ensure_board(character_id, week_start, db)

    newly_completed = []
    for wq in board:
        if wq.goal_type != goal_type or wq.is_completed:
            continue
        wq.progress += amount
        if wq.progress >= wq.goal_target:
            wq.is_completed = True
            newly_completed.append(wq.to_dict())

    return newly_completed


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
async def get_weekly_board(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí 4 weekly questy pro aktuálního hráče a jejich progress."""
    char       = await _get_char(user, db)
    now        = datetime.now(timezone.utc).replace(tzinfo=None)
    week_start = _week_start_for(now)
    week_end   = week_start + timedelta(days=7)

    board = await _ensure_board(char.id, week_start, db)
    await db.commit()

    return {
        "week_start": week_start.isoformat(),
        "week_end":   week_end.isoformat(),
        "quests":     [wq.to_dict() for wq in board],
    }


@router.post("/claim/{slot}")
async def claim_weekly_quest(
    slot: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nárokuje odměnu za splněný weekly quest (slot 0–3)."""
    char       = await _get_char(user, db)
    now        = datetime.now(timezone.utc).replace(tzinfo=None)
    week_start = _week_start_for(now)

    res = await db.execute(
        select(WeeklyQuestProgress).where(
            WeeklyQuestProgress.character_id == char.id,
            WeeklyQuestProgress.week_start   == week_start,
            WeeklyQuestProgress.slot         == slot,
        )
    )
    wq = res.scalar_one_or_none()

    if not wq:
        raise HTTPException(404, "Quest nenalezen.")
    if not wq.is_completed:
        raise HTTPException(400, "Quest ještě není splněn.")
    if wq.claimed:
        raise HTTPException(400, "Odměna již byla vybrána.")

    wq.claimed  = True
    char.xp    += wq.reward_xp
    char.gold  += wq.reward_gold
    await log_gold(
        db, char, wq.reward_gold, GoldReason.QUEST_REWARD,
        {"source": "weekly_board", "slot": slot, "goal_type": wq.goal_type},
    )

    leveled_up = []
    while char.xp >= xp_to_next(char.level):
        char.xp    -= xp_to_next(char.level)
        char.level += 1
        char.stat_points = (char.stat_points or 0) + 1
        leveled_up.append(char.level)
    if leveled_up:
        from routers.inventory import recalculate_with_gear
        await recalculate_with_gear(char, db)

    # Season Pass XP za claim weekly board questu
    from routers.season_pass import add_season_xp
    await add_season_xp(char.id, "weekly_claim", db)

    await db.commit()
    await db.refresh(char)

    label = wq.to_dict()["label"]
    return {
        "message":    f"Odměna za '{label}' vyzvednutá!",
        "xp_gained":  wq.reward_xp,
        "gold_gained": wq.reward_gold,
        "leveled_up": leveled_up,
        "character":  await char_dict_with_equipment(char, db),
    }
