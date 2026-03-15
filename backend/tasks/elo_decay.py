"""
tasks/elo_decay.py — Background job: ELO decay pro neaktivní hráče.

Logika:
- Hráč bez arénového zápasu 7+ dní ztrácí 5 ELO/den.
- Floor: 1000 (výchozí starting ELO — hráč neklesne níže).
- Job běží každých 24 hodin.

Multi-instance bezpečnost:
- Využívá DB-based distributed cron lock (models/cron_job.py).
- Pouze jedna instance spustí decay za daný interval.
- Odolné vůči souběžnému startu více instancí.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, and_

from database import AsyncSessionLocal
from models.character import Character
from models.arena import ArenaMatch
from models.cron_job import try_acquire_cron_lock
from core.logging import get_logger

log = get_logger(__name__)

DECAY_AMOUNT     = 5      # ELO ztráta za den neaktivity
INACTIVITY_DAYS  = 7      # Počet dní bez zápasu → začíná decay
ELO_FLOOR        = 1000   # Minimální ELO (výchozí ELO nového hráče)
INTERVAL_SECONDS = 86_400  # 24 hodin — minimální interval mezi spuštěními


async def run_elo_decay_once() -> int:
    """
    Aplikuje ELO decay jednou.
    Vrátí počet hráčů u kterých bylo ELO sníženo.
    Pokud v posledních 24 h již proběhl (na jakékoli instanci), vrátí 0.
    """
    from middleware.instance_id import INSTANCE_ID

    cutoff_activity = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=INACTIVITY_DAYS)

    async with AsyncSessionLocal() as db:
        # Distributed cron lock — pouze jedna instance za 24 h
        acquired = await try_acquire_cron_lock(
            name="elo_decay",
            min_interval_seconds=INTERVAL_SECONDS,
            db=db,
            instance_id=INSTANCE_ID,
        )
        if not acquired:
            log.info("ELO decay skipped (lock held by another instance or interval not elapsed)")
            return 0

        # Subquery: character_id kteří měli zápas po cutoff (aktivní hráči)
        active_attackers = (
            select(ArenaMatch.attacker_id)
            .where(ArenaMatch.played_at >= cutoff_activity)
            .scalar_subquery()
        )
        active_defenders = (
            select(ArenaMatch.defender_id)
            .where(ArenaMatch.played_at >= cutoff_activity)
            .scalar_subquery()
        )

        # Neaktivní hráči s ELO nad floorem
        result = await db.execute(
            select(Character).where(
                and_(
                    Character.arena_rank > ELO_FLOOR,
                    Character.id.not_in(active_attackers),
                    Character.id.not_in(active_defenders),
                )
            )
        )
        chars = result.scalars().all()

        for char in chars:
            char.arena_rank = max(ELO_FLOOR, char.arena_rank - DECAY_AMOUNT)

        if chars:
            await db.commit()

    today = datetime.now(timezone.utc).date()
    log.info(
        "ELO decay applied",
        extra={"data": {"affected": len(chars), "decay": DECAY_AMOUNT, "date": str(today), "instance": INSTANCE_ID}},
    )
    return len(chars)


async def elo_decay_loop() -> None:
    """
    Opakující se asyncio background task.
    Počká 60 s (server startup), pak spouští decay každých 24 hodin.
    """
    log.info(
        "ELO decay task starting",
        extra={"data": {"interval_hours": INTERVAL_SECONDS // 3600, "floor": ELO_FLOOR}},
    )
    await asyncio.sleep(60)  # nechej server inicializovat DB

    while True:
        try:
            count = await run_elo_decay_once()
            if count:
                log.info("ELO decay cycle complete", extra={"data": {"affected": count}})
        except asyncio.CancelledError:
            log.info("ELO decay task cancelled")
            return
        except Exception as exc:
            log.warning("ELO decay error", extra={"data": {"error": str(exc)}})

        try:
            await asyncio.sleep(INTERVAL_SECONDS)
        except asyncio.CancelledError:
            log.info("ELO decay task cancelled during sleep")
            return
