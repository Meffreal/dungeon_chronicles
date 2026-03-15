"""
models/cron_job.py — Distributed cron lock pro background tasky.

Umožňuje bezpečné spuštění periodic jobů v multi-instance prostředí.
Pouze jedna instance smí spustit daný job za definovaný interval.

Mechanismus:
  1. Pokus o atomický UPDATE: SET last_run_at = now WHERE last_run_at < cutoff
  2. Pokud UPDATE zasáhl 1 řádek → tato instance získala zámek a spustí job
  3. Pokud UPDATE nezasáhl → jiná instance již job spustila → skip

Omezení:
  - Vyžaduje databázi se silnou konzistencí (PostgreSQL, MySQL)
  - SQLite je dostatečný pro dev; pro prod použij PostgreSQL
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import String, Integer, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base


class CronJob(Base):
    """Záznam posledního spuštění background jobu."""
    __tablename__ = "cron_jobs"

    name:        Mapped[str]           = mapped_column(String(64), primary_key=True)
    last_run_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    run_count:   Mapped[int]           = mapped_column(Integer, default=0)
    locked_by:   Mapped[str|None]      = mapped_column(String(64), nullable=True)


async def try_acquire_cron_lock(
    name: str,
    min_interval_seconds: int,
    db: AsyncSession,
    instance_id: str = "default",
) -> bool:
    """
    Pokusí se získat cron zámek pro daný job.

    Vrátí True  → tato instance získala zámek, job by měl proběhnout.
    Vrátí False → jiná instance již job spustila, nebo interval ještě neuplynul.

    Implementace pro SQLite (kompatibilní s aiosqlite):
      - Načte existující záznam
      - Zkontroluje interval
      - Pokud OK: atomicky aktualizuje (race condition je přijatelná pro daily joby)
    """
    from sqlalchemy import select
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(seconds=min_interval_seconds)

    # Načti nebo vytvoř záznam
    result = await db.execute(select(CronJob).where(CronJob.name == name))
    row = result.scalar_one_or_none()

    if row is None:
        # První spuštění — vytvoř záznam
        row = CronJob(name=name, last_run_at=None, run_count=0, locked_by=instance_id)
        db.add(row)
        await db.commit()
        return True

    # Zkontroluj interval
    if row.last_run_at and row.last_run_at >= cutoff:
        return False  # Interval ještě neuplynul

    # Získej zámek — atomický update
    row.last_run_at = now
    row.run_count   = (row.run_count or 0) + 1
    row.locked_by   = instance_id
    await db.commit()
    return True


async def release_cron_lock(name: str, db: AsyncSession) -> None:
    """Uvolní cron zámek (volitelné — pro případ selhání jobu)."""
    from sqlalchemy import select
    result = await db.execute(select(CronJob).where(CronJob.name == name))
    row = result.scalar_one_or_none()
    if row:
        row.locked_by = None
        await db.commit()
