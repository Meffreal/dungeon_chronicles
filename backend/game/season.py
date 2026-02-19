"""
game/season.py — Logika sezón arény (start, ukončení, ELO reset, odměny)
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import AsyncSessionLocal
from models.arena import Season, SeasonResult, SEASON_DURATION_DAYS, get_season_reward
from models.character import Character
from models.notification import Notification, NotifType


def _soft_reset_elo(elo: int) -> int:
    """Sezónní ELO soft-reset: přibližuje se k 800."""
    return int(800 + max(0, elo - 800) * 0.4)


async def ensure_active_season(db: AsyncSession | None = None) -> Season:
    """Zajistí existenci aktivní sezóny. Pokud žádná není, vytvoří novou."""
    own_db = db is None
    if own_db:
        db = AsyncSessionLocal()

    try:
        result = await db.execute(
            select(Season).where(Season.is_active == True).order_by(Season.id.desc())
        )
        season = result.scalar_one_or_none()

        if season is None:
            # První sezóna
            now = datetime.utcnow()
            season = Season(
                number=1,
                start_at=now,
                end_at=now + timedelta(days=SEASON_DURATION_DAYS),
                is_active=True,
            )
            db.add(season)
            await db.commit()
            await db.refresh(season)
            print(f"[Season] Sezóna 1 zahájena, konec: {season.end_at}")

        return season
    finally:
        if own_db:
            await db.close()


async def process_expired_season(db: AsyncSession) -> Season | None:
    """
    Pokud aktivní sezóna expirovala:
    1. Zaznamená finální pořadí a odměny
    2. Soft-resetuje ELO všech hráčů
    3. Archivuje sezónu a spustí novou
    Vrátí novou sezónu nebo None pokud žádná sezóna neexpirovala.
    """
    result = await db.execute(
        select(Season).where(Season.is_active == True).order_by(Season.id.desc())
    )
    season = result.scalar_one_or_none()

    if season is None or not season.is_expired:
        return None

    print(f"[Season] Zpracovávám konec sezóny #{season.number}...")

    # Načti všechny postavy seřazené podle ELO
    chars_res = await db.execute(
        select(Character).order_by(Character.arena_rank.desc())
    )
    characters = chars_res.scalars().all()

    # Zaznamenej výsledky + připiš odměny + notifikace
    for rank, char in enumerate(characters, start=1):
        # Hráč musí mít alespoň 1 zápas aby dostal odměnu
        if char.arena_wins + char.arena_losses == 0:
            continue

        reward = get_season_reward(rank)

        sr = SeasonResult(
            season_id=season.id,
            character_id=char.id,
            final_rank=rank,
            final_elo=char.arena_rank,
            reward_gold=reward,
            reward_claimed=False,
        )
        db.add(sr)

        # Notifikace
        db.add(Notification(
            character_id=char.id,
            type=NotifType.SYSTEM,
            title=f"Sezóna {season.number} skončila!",
            body=f"Tvoje finální pořadí: #{rank} (ELO: {char.arena_rank}). Odměna: {reward} G — vyzvedni si ji v Aréně.",
        ))

        # Soft ELO reset
        char.arena_rank = _soft_reset_elo(char.arena_rank)

    # Uzavři starou sezónu
    season.is_active = False

    # Vytvoř novou
    now = datetime.utcnow()
    new_season = Season(
        number=season.number + 1,
        start_at=now,
        end_at=now + timedelta(days=SEASON_DURATION_DAYS),
        is_active=True,
    )
    db.add(new_season)
    await db.commit()
    await db.refresh(new_season)

    print(f"[Season] Sezóna #{new_season.number} zahájena.")
    return new_season
