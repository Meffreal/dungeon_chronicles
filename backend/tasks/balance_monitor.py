"""
tasks/balance_monitor.py — Denní background job pro detekci balance anomálií.

Detekované anomálie:
  1. arena_winrate  — win rate jedné třídy > 60% v arénách (posledních 7 dní)
  2. gold_monopoly  — top 10 hráčů vlastní > 40% veškerého goldu
  3. gold_farm      — denní arena gold příjmy > 3× expected cap (indikátor exploitu)
  4. season_skew    — top 1 hráč má 5× více wins než top 2 (aktivní sezóna)

Každá anomálie se zapíše do DB jako BalanceAlert.
Duplicity (stejný typ + neresolved) se nepřidávají.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_

from database import AsyncSessionLocal
from models.balance_alert import BalanceAlert
from models.character import Character
from models.arena import ArenaMatch, Season, SeasonResult
from models.economy import GoldTransaction, GoldReason
from models.cron_job import try_acquire_cron_lock
from core.logging import get_logger

log = get_logger(__name__)

INTERVAL_SECONDS = 86_400  # 24 hodin

# Thresholdy
WINRATE_THRESHOLD   = 0.60   # 60% win rate → alert
MONOPOLY_THRESHOLD  = 0.40   # top 10 vlastní > 40% goldu → alert
FARM_MULTIPLIER     = 3.0    # denní gold farm > 3× expected → alert
SEASON_SKEW_RATIO   = 5.0    # top1 wins > 5× top2 wins → alert

# Expected arena gold cap: průměrný hráč by měl mít max ~1 500 G/den z arény
EXPECTED_DAILY_ARENA_GOLD = 1_500


async def _upsert_alert(db, alert_type: str, severity: str, title: str, detail: str) -> bool:
    """
    Přidá alert pokud stejný typ ještě není neresolved.
    Vrátí True pokud byl alert přidán.
    """
    existing = (await db.execute(
        select(BalanceAlert).where(
            and_(BalanceAlert.alert_type == alert_type, BalanceAlert.resolved == False)
        )
    )).scalar_one_or_none()

    if existing:
        return False  # Již existuje neresolved alert tohoto typu

    alert = BalanceAlert(
        alert_type=alert_type,
        severity=severity,
        title=title,
        detail=detail,
    )
    db.add(alert)
    return True


async def _check_arena_winrate(db) -> list[str]:
    """Detekuje třídu s win rate > 60% (posledních 7 dní)."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    alerts = []

    # Celkové zápasy per třída útočníka/obránce
    recent_matches = (
        select(ArenaMatch.attacker_id, ArenaMatch.defender_id, ArenaMatch.winner_id)
        .where(ArenaMatch.played_at >= cutoff)
        .subquery()
    )

    # Subquery: character_id → cls (třída)
    attacker_chars = (
        select(Character.id, Character.cls)
        .subquery()
    )

    # Wins: winner_id → char_class
    wins_per_class_q = await db.execute(
        select(attacker_chars.c.char_class, func.count().label("wins"))
        .join(recent_matches, attacker_chars.c.id == recent_matches.c.winner_id)
        .group_by(attacker_chars.c.char_class)
    )
    wins_per_class = {row.char_class: row.wins for row in wins_per_class_q}

    # Total matches per třída (jako útočník nebo obránce)
    total_as_attacker_q = await db.execute(
        select(attacker_chars.c.char_class, func.count().label("cnt"))
        .join(recent_matches, attacker_chars.c.id == recent_matches.c.attacker_id)
        .group_by(attacker_chars.c.char_class)
    )
    total_as_defender_q = await db.execute(
        select(attacker_chars.c.char_class, func.count().label("cnt"))
        .join(recent_matches, attacker_chars.c.id == recent_matches.c.defender_id)
        .group_by(attacker_chars.c.char_class)
    )

    totals: dict[str, int] = {}
    for row in total_as_attacker_q:
        totals[row.char_class] = totals.get(row.char_class, 0) + row.cnt
    for row in total_as_defender_q:
        totals[row.char_class] = totals.get(row.char_class, 0) + row.cnt

    for cls, total in totals.items():
        if total < 10:
            continue  # Příliš málo dat
        wins = wins_per_class.get(cls, 0)
        winrate = wins / total
        if winrate > WINRATE_THRESHOLD:
            pct = round(winrate * 100, 1)
            added = await _upsert_alert(
                db,
                alert_type="arena_winrate",
                severity="warning",
                title=f"Arena win rate anomálie: {cls}",
                detail=f"Třída '{cls}' má {pct}% win rate (threshold: {int(WINRATE_THRESHOLD*100)}%) za posledních 7 dní. Wins: {wins}/{total}.",
            )
            if added:
                alerts.append(f"arena_winrate:{cls}:{pct}%")

    return alerts


async def _check_gold_monopoly(db) -> list[str]:
    """Detekuje koncentraci goldu — top 10 vlastní > 40% celku."""
    total_gold_q = await db.execute(select(func.sum(Character.gold)))
    total_gold = total_gold_q.scalar_one() or 0

    if total_gold == 0:
        return []

    top10_q = await db.execute(
        select(func.sum(Character.gold))
        .select_from(
            select(Character.gold).order_by(Character.gold.desc()).limit(10).subquery()
        )
    )
    top10_gold = top10_q.scalar_one() or 0

    ratio = top10_gold / total_gold
    if ratio > MONOPOLY_THRESHOLD:
        pct = round(ratio * 100, 1)
        added = await _upsert_alert(
            db,
            alert_type="gold_monopoly",
            severity="warning",
            title="Gold monopoly detekován",
            detail=f"Top 10 hráčů vlastní {pct}% veškerého goldu (threshold: {int(MONOPOLY_THRESHOLD*100)}%). Top10: {top10_gold:,}G / Total: {total_gold:,}G.",
        )
        return [f"gold_monopoly:{pct}%"] if added else []

    return []


async def _check_gold_farm(db) -> list[str]:
    """Detekuje nadměrný denní gold farm z arény (exploit indikátor)."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)

    arena_gold_q = await db.execute(
        select(func.sum(GoldTransaction.amount))
        .where(
            and_(
                GoldTransaction.reason == GoldReason.ARENA_REWARD.value,
                GoldTransaction.timestamp >= cutoff,
                GoldTransaction.amount > 0,
            )
        )
    )
    total_arena_gold = arena_gold_q.scalar_one() or 0

    # Spočítej počet aktivních hráčů (kteří hráli arenu dnes)
    active_players_q = await db.execute(
        select(func.count(func.distinct(ArenaMatch.attacker_id)))
        .where(ArenaMatch.played_at >= cutoff)
    )
    active_players = active_players_q.scalar_one() or 1

    expected_total = EXPECTED_DAILY_ARENA_GOLD * active_players
    if expected_total > 0 and total_arena_gold > FARM_MULTIPLIER * expected_total:
        ratio = round(total_arena_gold / expected_total, 1)
        added = await _upsert_alert(
            db,
            alert_type="gold_farm",
            severity="critical",
            title="Podezřelý arena gold farm (možný exploit)",
            detail=f"Denní arena gold: {total_arena_gold:,}G při {active_players} hráčích ({ratio}× expected cap). Očekáváno max: {int(FARM_MULTIPLIER * expected_total):,}G.",
        )
        return [f"gold_farm:{total_arena_gold}G:{ratio}x"] if added else []

    return []


async def _check_season_skew(db) -> list[str]:
    """Detekuje sezónní skew — top 1 má 5× více wins než top 2."""
    active_season = (await db.execute(
        select(Season).where(Season.is_active == True)
    )).scalar_one_or_none()

    if not active_season:
        return []

    # Seřaď hráče dle final_elo (proxy pro wins) v aktivní sezóně
    top2_q = await db.execute(
        select(SeasonResult.character_id, SeasonResult.final_elo, SeasonResult.final_rank)
        .where(SeasonResult.season_id == active_season.id)
        .order_by(SeasonResult.final_rank.asc())
        .limit(2)
    )
    top2 = top2_q.all()

    if len(top2) < 2:
        return []

    top1_elo = top2[0].final_elo or 0
    top2_elo = top2[1].final_elo or 1

    if top2_elo > 0 and top1_elo >= SEASON_SKEW_RATIO * top2_elo:
        ratio = round(top1_elo / top2_elo, 1)
        added = await _upsert_alert(
            db,
            alert_type="season_skew",
            severity="warning",
            title="Season ELO skew detekován",
            detail=f"Top 1 hráč (ELO {top1_elo}) má {ratio}× více ELO než top 2 (ELO {top2_elo}). Sezóna #{active_season.number}.",
        )
        return [f"season_skew:{ratio}x"] if added else []

    return []


async def run_balance_monitor_once() -> int:
    """
    Spustí všechny balance checks jednou.
    Vrátí počet nových alertů.
    Pokud v posledních 24 h již proběhl, vrátí 0.
    """
    from middleware.instance_id import INSTANCE_ID

    async with AsyncSessionLocal() as db:
        acquired = await try_acquire_cron_lock(
            name="balance_monitor",
            min_interval_seconds=INTERVAL_SECONDS,
            db=db,
            instance_id=INSTANCE_ID,
        )
        if not acquired:
            log.info("Balance monitor skipped (lock held or interval not elapsed)")
            return 0

        new_alerts: list[str] = []

        try:
            new_alerts += await _check_arena_winrate(db)
        except Exception as e:
            log.warning("Balance monitor: arena_winrate check failed", extra={"data": {"error": str(e)}})

        try:
            new_alerts += await _check_gold_monopoly(db)
        except Exception as e:
            log.warning("Balance monitor: gold_monopoly check failed", extra={"data": {"error": str(e)}})

        try:
            new_alerts += await _check_gold_farm(db)
        except Exception as e:
            log.warning("Balance monitor: gold_farm check failed", extra={"data": {"error": str(e)}})

        try:
            new_alerts += await _check_season_skew(db)
        except Exception as e:
            log.warning("Balance monitor: season_skew check failed", extra={"data": {"error": str(e)}})

        if new_alerts:
            await db.commit()

    log.info(
        "Balance monitor cycle complete",
        extra={"data": {"new_alerts": len(new_alerts), "alerts": new_alerts}},
    )
    return len(new_alerts)


async def balance_monitor_loop() -> None:
    """
    Opakující se asyncio background task.
    Počká 90 s (server startup), pak spouští checks každých 24 hodin.
    """
    log.info("Balance monitor task starting", extra={"data": {"interval_hours": 24}})
    await asyncio.sleep(90)

    while True:
        try:
            count = await run_balance_monitor_once()
            if count:
                log.info("Balance monitor: new alerts created", extra={"data": {"count": count}})
        except asyncio.CancelledError:
            log.info("Balance monitor task cancelled")
            return
        except Exception as exc:
            log.warning("Balance monitor error", extra={"data": {"error": str(exc)}})

        try:
            await asyncio.sleep(INTERVAL_SECONDS)
        except asyncio.CancelledError:
            log.info("Balance monitor task cancelled during sleep")
            return
