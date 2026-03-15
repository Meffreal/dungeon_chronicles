"""
routers/gambler.py — Šarlatán: sázky, Shadow House, loterie
"""
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db
from models.economy import log_gold, GoldReason
from models.user import User
from models.character import Character
from models.gambler import (
    Bet, Lottery, LotteryEntry,
    BET_MAX_OPEN, BET_MIN_STAKE, LOTTERY_MIN_PLAYERS,
    SHADOW_HOUSE_EDGE, SHADOW_HOUSE_SUSPICION_THRESHOLD,
    SHADOW_HOUSE_SUSPICION_ODDS_PENALTY, GAMBLER_XP,
)
from models.quest import QUEST_DEFINITIONS
from game.professions import get_char, require_active_profession, award_xp
from routers.auth import get_current_user

router = APIRouter(prefix="/gambler", tags=["gambler"])

SHADOW_HOUSE_BET_TYPES = ["quest_success", "quest_drop_rarity", "arena_outcome"]


# ── Schemas ───────────────────────────────────────────────────────────────────

class PlaceBetRequest(BaseModel):
    bet_type:          str     # quest_success | quest_drop_rarity | arena_outcome
    subject_id:        int     # quest_def_id nebo arena match ID
    subject_type:      str     # quest | arena
    prediction:        str     # success | fail | epic | ...
    stake:             int     # zlato
    target_char_id:    int | None = None  # None = Shadow House

class AcceptBetRequest(BaseModel):
    bet_id: int

class CreateLotteryRequest(BaseModel):
    entry_fee: int
    draw_after_minutes: int = 60    # kdy se automaticky losuje

class EnterLotteryRequest(BaseModel):
    lottery_id: int


# ── Helpery ───────────────────────────────────────────────────────────────────

async def _count_open_bets(char_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Bet.id)).where(
            Bet.bettor_char_id == char_id,
            Bet.status == "open",
        )
    )
    return result.scalar_one()


async def _shadow_house_suspicion(char_id: int, db: AsyncSession) -> float:
    """Vrátí aktuální odds penalty pro Shadow House sázky (0.0–0.4)."""
    # Načti VŠECHNY poslední NPC sázky (ne jen výhry) — jinak nelze počítat konsekvutiní sérii
    result = await db.execute(
        select(Bet).where(
            Bet.bettor_char_id == char_id,
            Bet.is_vs_npc == True,
            Bet.status == "resolved",
        ).order_by(Bet.resolved_at.desc()).limit(SHADOW_HOUSE_SUSPICION_THRESHOLD + 5)
    )
    recent_bets = result.scalars().all()

    # Počítej konsekvutivní výhry od nejnovější sázky
    consecutive = 0
    for bet in recent_bets:
        if bet.result == "win":
            consecutive += 1
        else:
            break  # série přerušena prohrou

    if consecutive >= SHADOW_HOUSE_SUSPICION_THRESHOLD:
        return SHADOW_HOUSE_SUSPICION_ODDS_PENALTY * (consecutive - SHADOW_HOUSE_SUSPICION_THRESHOLD + 1)
    return 0.0


# ── Endpointy ─────────────────────────────────────────────────────────────────

@router.get("/bets")
async def my_bets(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Sázky hráče — otevřené i uzavřené."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    result = await db.execute(
        select(Bet)
        .options(selectinload(Bet.target))
        .where(Bet.bettor_char_id == char.id)
        .order_by(Bet.created_at.desc())
        .limit(30)
    )
    bets = result.scalars().all()
    return {"bets": [b.to_dict() for b in bets], "max_open": BET_MAX_OPEN}


@router.get("/shadow-house")
async def shadow_house_menu(
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Nabídky Shadow House — k dispozici vždy, ale s house edge a suspicion."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    suspicion = await _shadow_house_suspicion(char.id, db)
    edge = SHADOW_HOUSE_EDGE + suspicion

    # Denní speciální sázka: náhodný quest s vyšším payoutem
    today_seed = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y%m%d") + str(char.id)
    rng = random.Random(today_seed)
    daily_quest = rng.choice(QUEST_DEFINITIONS)

    return {
        "house_edge":        round(edge * 100, 1),
        "suspicion_penalty": round(suspicion * 100, 1),
        "note": "Čím víc výher v řadě, tím horší odds nabídne Shadow House.",
        "daily_special": {
            "quest_id":   daily_quest[0],
            "quest_name": daily_quest[1],
            "type":       "quest_success",
            "payout_multiplier": round((1 - edge) * 2.0, 2),   # ~1.7× při nulové suspicion
        },
        "standard_offers": [
            {
                "type":    "quest_success",
                "desc":    "Sázej na úspěch / neúspěch svého questu",
                "payout":  round((1 - edge) * 2.0, 2),
            },
            {
                "type":    "quest_drop_rarity",
                "desc":    "Sázej na raritu dropu",
                "payout":  round((1 - edge) * 3.5, 2),   # těžší odhadnout
            },
            {
                "type":    "arena_outcome",
                "desc":    "Sázej na výsledek tvého arénového útoku",
                "payout":  round((1 - edge) * 1.8, 2),
            },
        ],
    }


@router.post("/bet")
async def place_bet(
    req:  PlaceBetRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Otevře novou sázku. Target = None → vs Shadow House.
    Zlato se strhne okamžitě (escrow).
    """
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    if req.stake < BET_MIN_STAKE:
        raise HTTPException(400, f"Minimální sázka je {BET_MIN_STAKE} G.")
    if char.gold < req.stake:
        raise HTTPException(400, f"Nedostatek zlata. Máš {char.gold} G, potřebuješ {req.stake} G.")

    open_count = await _count_open_bets(char.id, db)
    if open_count >= BET_MAX_OPEN:
        raise HTTPException(400, f"Maximálně {BET_MAX_OPEN} otevřených sázek najednou.")

    is_vs_npc = (req.target_char_id is None)

    if not is_vs_npc:
        # Ověř existenci cíle
        target_res = await db.execute(
            select(Character).where(Character.id == req.target_char_id)
        )
        target = target_res.scalar_one_or_none()
        if not target:
            raise HTTPException(404, "Cílový hráč nenalezen.")
        if req.target_char_id == char.id:
            raise HTTPException(400, "Nemůžeš sázet sám se sebou.")
        target_stake = req.stake   # symetrická sázka
        npc_penalty = 0.0
    else:
        suspicion = await _shadow_house_suspicion(char.id, db)
        edge = SHADOW_HOUSE_EDGE + suspicion
        payout_mult = (1 - edge) * 2.0
        target_stake = int(req.stake * payout_mult)
        npc_penalty = suspicion

    # Strhni zlato (escrow)
    char.gold -= req.stake
    await log_gold(db, char, -req.stake, GoldReason.GAMBLER_BET,
                   {"bet_type": req.bet_type, "stake": req.stake})

    bet = Bet(
        bettor_char_id=char.id,
        target_char_id=req.target_char_id,
        bet_type=req.bet_type,
        subject_id=req.subject_id,
        subject_type=req.subject_type,
        bettor_prediction=req.prediction,
        bettor_stake=req.stake,
        target_stake=target_stake,
        is_vs_npc=is_vs_npc,
        npc_odds_penalty=npc_penalty,
        status="open",
    )
    # Předvyplň relationship aby bet.to_dict() nemuselo dělat lazy load
    if not is_vs_npc and target:
        bet.target = target
    db.add(bet)

    xp_result = await award_xp(char.id, "broker", GAMBLER_XP["bet_placed"], db)
    await db.commit()
    await db.refresh(bet)

    return {
        "message":        "Sázka otevřena!",
        "bet":            bet.to_dict(),
        "gold_escrowed":  req.stake,
        "potential_win":  target_stake,
        "xp_result":      xp_result,
    }


@router.post("/bet/{bet_id}/accept")
async def accept_bet(
    bet_id: int,
    user:   User = Depends(get_current_user),
    db:     AsyncSession = Depends(get_db),
):
    """
    Cílový hráč přijme sázku. Tím stvrdí podmínky a složí svůj stake.
    Nelze přijmout NPC sázky (Shadow House).
    """
    char = await get_char(user, db)

    # selectinload(Bet.target) je nutný — jinak bet.to_dict() způsobí MissingGreenlet při přístupu na target.name
    bet_res = await db.execute(
        select(Bet).options(selectinload(Bet.target)).where(Bet.id == bet_id)
    )
    bet = bet_res.scalar_one_or_none()
    if not bet:
        raise HTTPException(404, "Sázka nenalezena.")
    if bet.is_vs_npc:
        raise HTTPException(400, "Shadow House sázky nelze přijmout — probíhají automaticky.")
    if bet.target_char_id != char.id:
        raise HTTPException(403, "Tato sázka není pro tebe.")
    if bet.status != "open":
        raise HTTPException(400, "Sázka již není otevřena.")
    if char.gold < bet.target_stake:
        raise HTTPException(400, f"Nedostatek zlata. Potřebuješ {bet.target_stake} G.")

    char.gold -= bet.target_stake
    await log_gold(db, char, -bet.target_stake, GoldReason.GAMBLER_BET,
                   {"bet_id": bet.id, "role": "target"})
    bet.status = "accepted"
    bet.accepted_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    return {
        "message":        "Sázka přijata!",
        "bet":            bet.to_dict(),
        "gold_escrowed":  bet.target_stake,
    }


@router.get("/lotteries")
async def list_lotteries(
    db: AsyncSession = Depends(get_db),
):
    """Aktivní loterie na serveru."""
    result = await db.execute(
        select(Lottery)
        .options(selectinload(Lottery.organizer), selectinload(Lottery.entries))
        .where(Lottery.status == "open")
        .order_by(Lottery.created_at.desc())
    )
    lotteries = result.scalars().all()
    return {"lotteries": [l.to_dict() for l in lotteries]}


@router.post("/lottery/create")
async def create_lottery(
    req:  CreateLotteryRequest,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Šarlatán vytvoří loterii. XP dostane za organizaci (flat, při draw)."""
    char = await get_char(user, db)
    await require_active_profession(char.id, "broker", db)

    if req.entry_fee < 10:
        raise HTTPException(400, "Minimální vstupní poplatek je 10 G.")
    if req.draw_after_minutes < 10:
        raise HTTPException(400, "Loterie musí běžet alespoň 10 minut.")

    lottery = Lottery(
        organizer_char_id=char.id,
        entry_fee=req.entry_fee,
        draw_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=req.draw_after_minutes),
    )
    # Předvyplň relationship aby lottery.to_dict() nemuselo dělat lazy load na organizer.name
    lottery.organizer = char
    db.add(lottery)
    await db.commit()
    await db.refresh(lottery)

    return {
        "message":  "Loterie vytvořena!",
        "lottery":  lottery.to_dict(),
    }


@router.post("/lottery/{lottery_id}/enter")
async def enter_lottery(
    lottery_id: int,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """Hráč vstoupí do loterie zaplacením entry_fee."""
    char = await get_char(user, db)

    lottery_res = await db.execute(
        select(Lottery)
        .options(selectinload(Lottery.entries))
        .where(Lottery.id == lottery_id)
    )
    lottery = lottery_res.scalar_one_or_none()
    if not lottery:
        raise HTTPException(404, "Loterie nenalezena.")
    if lottery.status != "open":
        raise HTTPException(400, "Tato loterie již není otevřena.")
    if char.gold < lottery.entry_fee:
        raise HTTPException(400, f"Nedostatek zlata. Vstupné: {lottery.entry_fee} G.")

    # Kontrola duplicitního vstupu
    already = any(e.character_id == char.id for e in lottery.entries)
    if already:
        raise HTTPException(400, "Už jsi v této loterii.")

    char.gold -= lottery.entry_fee
    await log_gold(db, char, -lottery.entry_fee, GoldReason.GAMBLER_LOTTERY,
                   {"lottery_id": lottery.id})
    lottery.pool_total += lottery.entry_fee

    entry = LotteryEntry(lottery_id=lottery.id, character_id=char.id)
    db.add(entry)
    await db.commit()

    return {
        "message":    f"Vstoupil jsi do loterie! Pool: {lottery.pool_total} G.",
        "entry_fee":  lottery.entry_fee,
        "pool_total": lottery.pool_total,
    }


@router.post("/lottery/{lottery_id}/draw")
async def draw_lottery(
    lottery_id: int,
    user: User = Depends(get_current_user),
    db:   AsyncSession = Depends(get_db),
):
    """
    Organizátor spustí losování (nebo kdokoli pokud uplynul draw_at čas).
    Vítěz bere celý pool, Šarlatán dostane XP.
    """
    char = await get_char(user, db)

    lottery_res = await db.execute(
        select(Lottery)
        .options(selectinload(Lottery.entries), selectinload(Lottery.organizer))
        .where(Lottery.id == lottery_id)
    )
    lottery = lottery_res.scalar_one_or_none()
    if not lottery:
        raise HTTPException(404, "Loterie nenalezena.")
    if lottery.status != "open":
        raise HTTPException(400, "Loterie není aktivní.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    is_organizer = (lottery.organizer_char_id == char.id)
    time_expired = lottery.draw_at and now >= lottery.draw_at.replace(tzinfo=None)

    if not is_organizer and not time_expired:
        raise HTTPException(403, "Jen organizátor může spustit losování před uplynutím času.")

    if not lottery.can_draw:
        # Zruš loterii
        lottery.status = "cancelled"
        await db.commit()
        return {
            "message":  f"Loterie zrušena — přihlásilo se méně než {LOTTERY_MIN_PLAYERS} hráčů. Vstupné vráceno.",
            "cancelled": True,
        }

    # Vyber vítěze
    winner_entry = random.choice(lottery.entries)
    winner_res = await db.execute(
        select(Character).where(Character.id == winner_entry.character_id)
    )
    winner = winner_res.scalar_one_or_none()
    if winner:
        winner.gold += lottery.pool_total
        await log_gold(db, winner, lottery.pool_total, GoldReason.GAMBLER_WIN,
                       {"lottery_id": lottery.id, "pool": lottery.pool_total})

    lottery.status = "completed"
    lottery.winner_char_id = winner_entry.character_id
    lottery.drawn_at = now

    # XP organizátorovi
    xp_result = {"awarded": False}
    if not lottery.xp_awarded:
        xp_result = await award_xp(lottery.organizer_char_id, "broker", GAMBLER_XP["lottery_organized"], db)
        lottery.xp_awarded = True

    await db.commit()

    return {
        "message":    f"Vyhrál '{winner.name if winner else '?'}' a bere {lottery.pool_total} G!",
        "winner":     winner.name if winner else "?",
        "pool_total": lottery.pool_total,
        "xp_result":  xp_result,
    }


# ── Interní hook: resolve sázky po questu / arénové bitvě ────────────────────

async def resolve_quest_bets(
    char_id:       int,
    quest_def_id:  int,
    actual_success: bool,
    actual_rarity:  str | None,
    db: AsyncSession,
) -> None:
    """
    Volá se z quest collect. Uzavře všechny sázky kde subject = tento quest.
    """
    result = await db.execute(
        select(Bet).where(
            Bet.bettor_char_id == char_id,
            Bet.subject_type == "quest",
            Bet.subject_id == quest_def_id,
            Bet.status.in_(["open", "accepted"]),
        )
    )
    bets = result.scalars().all()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for bet in bets:
        actual = None
        if bet.bet_type == "quest_success":
            actual = "success" if actual_success else "fail"
        elif bet.bet_type == "quest_drop_rarity":
            actual = actual_rarity

        won = (actual is not None and bet.bettor_prediction == actual)
        bet.status = "resolved"
        bet.result = "win" if won else "loss"
        bet.resolved_at = now

        bettor_res = await db.execute(select(Character).where(Character.id == bet.bettor_char_id))
        bettor = bettor_res.scalar_one_or_none()

        if won:
            payout = bet.bettor_stake + bet.target_stake
            if bettor:
                bettor.gold += payout
                await log_gold(db, bettor, payout, GoldReason.GAMBLER_WIN,
                               {"bet_id": bet.id})
            # Vrať stake protistranám (u NPC = jen výhra, stake zpět)
            if not bet.is_vs_npc and bet.target_char_id:
                pass  # target prohrál svůj stake — nic nevrací
            xp_key = "bet_won_vs_npc" if bet.is_vs_npc else "bet_won_vs_player"
            if not bet.xp_awarded:
                await award_xp(bet.bettor_char_id, "broker", GAMBLER_XP[xp_key], db)
                bet.xp_awarded = True
        else:
            # Prohra — stake propadl, vrať escrow protistraně (u NPC = Shadow House bere)
            if not bet.is_vs_npc and bet.target_char_id:
                target_res = await db.execute(
                    select(Character).where(Character.id == bet.target_char_id)
                )
                target = target_res.scalar_one_or_none()
                if target:
                    target.gold += bet.bettor_stake + bet.target_stake
                    await log_gold(db, target, bet.bettor_stake + bet.target_stake,
                                   GoldReason.GAMBLER_WIN, {"bet_id": bet.id})
            if not bet.xp_awarded:
                await award_xp(bet.bettor_char_id, "broker", GAMBLER_XP["bet_lost"], db)
                bet.xp_awarded = True
