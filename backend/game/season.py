"""
game/season.py — Logika sezón arény (start, ukončení, ELO reset, odměny)
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import AsyncSessionLocal
from models.arena import Season, SeasonResult, SEASON_DURATION_DAYS, get_season_reward, get_season_cosmetics
from models.character import Character
from models.notification import Notification, NotifType
from core.logging import get_logger

log = get_logger(__name__)

# Témata sezón — mapuje číslo sezóny na (název, lore text).
# Pro sezóny mimo rozsah se cyklí přes seznam.
SEASON_THEMES: dict[int, tuple[str, str]] = {
    1: (
        "Úsvit Gladiátorů",
        "Arény se otevírají poprvé po staletích nečinnosti. "
        "Hrdinové ze všech koutů světa přicházejí dokázat svou hodnotu. "
        "Toto je teprve začátek — a přesto se již píší legendy.",
    ),
    2: (
        "Krvavá Luna",
        "Pod nachově rudou lunou se arena mění v bojiště bezuzdné síly. "
        "Stará prokletí se probouzejí a dotýkají těch nejodvážnějších bojovníků. "
        "Jen nejsilnější přežijí tuto noc.",
    ),
    3: (
        "Stín Drakona",
        "Ze severu přicházejí zprávy o probuzení starověkého draka. "
        "Arény přitahují hrdiny hledající slávu dřív, než se temnota rozšíří. "
        "Boj je zkouškou připravenosti na věci, které teprve přijdou.",
    ),
    4: (
        "Věk Prachu",
        "Staré ruiny promluvily — pradávná válka se nevzdala svých hráčů. "
        "Duchové padlých gladiátorů hlídají arénu a hodnotí každý úder. "
        "Kdo zvítězí, získá přízeň zapomenutých bohů.",
    ),
    5: (
        "Ledový Hněv",
        "Třeskutý sever seslal své nejlepší válečníky, omotané v kožešinách a hněvu. "
        "Arénní písek je zmrzlý, dech páří ve vzduchu a každé vítězství je vytesáno do ledu. "
        "Zima nemiluje slabé.",
    ),
    6: (
        "Zlatá Vichřice",
        "Kupci a mecenáši ze čtyř stran světa vsadili svá jmění na tuto sezónu. "
        "Arénní trhy bzučí zlatem a sázkami, bojovníci se stali živou legendou. "
        "Sláva i bohatství — tentokrát jsou v sázce obojí.",
    ),
    7: (
        "Temné Záblesky",
        "Mágové porušili staré smlouvy a arénní prostor prostupují zakázané energie. "
        "Každé kouzlo září jinak a každý útok nese tajemný otisk. "
        "Tato sezóna patří těm, kdo ovládají temnotu.",
    ),
    8: (
        "Zpěv Oceli",
        "Kovářský cech ohlásil turnaj cti zasvěcený řemeslu boje. "
        "Rytíři v plné zbroji přicházejí s kodexem a čepelí. "
        "Arénní kov zpívá — a ten zpěv nezmlkne dřív, než padne poslední nepřítel.",
    ),
}

_THEME_CYCLE = list(SEASON_THEMES.values())


def _get_season_theme(number: int) -> tuple[str, str]:
    """Vrátí (theme_name, theme_lore) pro dané číslo sezóny (cyklí po vyčerpání)."""
    if number in SEASON_THEMES:
        return SEASON_THEMES[number]
    idx = (number - 1) % len(_THEME_CYCLE)
    return _THEME_CYCLE[idx]


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
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            t_name, t_lore = _get_season_theme(1)
            season = Season(
                number=1,
                start_at=now,
                end_at=now + timedelta(days=SEASON_DURATION_DAYS),
                is_active=True,
                theme_name=t_name,
                theme_lore=t_lore,
            )
            db.add(season)
            await db.commit()
            await db.refresh(season)
            log.info("Season started", extra={"data": {"number": 1, "end_at": str(season.end_at)}})

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

    log.info("Season ending", extra={"data": {"number": season.number}})

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
        cosmetic_title, cosmetic_frame = get_season_cosmetics(rank)

        sr = SeasonResult(
            season_id=season.id,
            character_id=char.id,
            final_rank=rank,
            final_elo=char.arena_rank,
            reward_gold=reward,
            reward_claimed=False,
            reward_title=cosmetic_title,
            reward_frame=cosmetic_frame,
        )
        db.add(sr)

        # Notifikace — zmíníme i kosmetiku pokud byla přidělena
        cosmetic_hint = ""
        if cosmetic_frame:
            cosmetic_hint = f" + exkluzivní portrait frame \"{cosmetic_frame}\""
        elif cosmetic_title:
            cosmetic_hint = f" + titul \"{cosmetic_title}\""

        db.add(Notification(
            character_id=char.id,
            type=NotifType.SYSTEM,
            title=f"Sezóna {season.number} skončila!",
            body=(
                f"Tvoje finální pořadí: #{rank} (ELO: {char.arena_rank}). "
                f"Odměna: {reward} G{cosmetic_hint} — vyzvedni si ji v Aréně."
            ),
        ))

        # Soft ELO reset
        char.arena_rank = _soft_reset_elo(char.arena_rank)

    # Uzavři starou sezónu
    season.is_active = False

    # Vytvoř novou
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    new_number = season.number + 1
    t_name, t_lore = _get_season_theme(new_number)
    new_season = Season(
        number=new_number,
        start_at=now,
        end_at=now + timedelta(days=SEASON_DURATION_DAYS),
        is_active=True,
        theme_name=t_name,
        theme_lore=t_lore,
    )
    db.add(new_season)
    await db.commit()
    await db.refresh(new_season)

    log.info("Season started", extra={"data": {"number": new_season.number, "end_at": str(new_season.end_at)}})
    return new_season
