"""
game/season_pass_manager.py — Správa aktivní sezóny (SeasonPass)
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import AsyncSessionLocal
from models.season_pass import SeasonPass, SEASON_PASS_DURATION_DAYS
from core.logging import get_logger

log = get_logger(__name__)


async def ensure_active_season_pass(db: AsyncSession | None = None) -> SeasonPass:
    """Zajistí existenci aktivní sezóny. Pokud žádná není, vytvoří novou."""
    own_db = db is None
    if own_db:
        db = AsyncSessionLocal()

    try:
        result = await db.execute(
            select(SeasonPass)
            .where(SeasonPass.is_active == True)
            .order_by(SeasonPass.id.desc())
        )
        season = result.scalar_one_or_none()

        if season is None:
            # Najdi číslo poslední sezóny
            last_res = await db.execute(
                select(SeasonPass).order_by(SeasonPass.id.desc()).limit(1)
            )
            last = last_res.scalar_one_or_none()
            num = (last.season_num + 1) if last else 1

            now = datetime.now(timezone.utc).replace(tzinfo=None)
            season = SeasonPass(
                season_num=num,
                name=f"Sezóna {num}",
                start_date=now,
                end_date=now + timedelta(days=SEASON_PASS_DURATION_DAYS),
                is_active=True,
            )
            db.add(season)
            await db.commit()
            await db.refresh(season)
            log.info("Season pass created", extra={"data": {"season": num}})
        else:
            # Zkontroluj expiraci
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if season.end_date < now:
                season.is_active = False
                await db.commit()
                # Rekurzivně vytvoř novou
                return await ensure_active_season_pass(db if not own_db else None)

        return season
    finally:
        if own_db:
            await db.close()
