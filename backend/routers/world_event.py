"""
routers/world_event.py — World Events systém (komunální sezónní cíle)
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db, AsyncSessionLocal
from core.logging import get_logger
from models.user import User
from models.character import Character
from models.world_event import (
    WorldEvent, WorldEventContrib, WorldEventClaim,
    WORLD_EVENT_DEFINITIONS,
)
from models.economy import GoldReason
from routers.auth import get_current_user
from routers.crystals import add_crystals

log = get_logger(__name__)
router = APIRouter(prefix="/world-events", tags=["world-events"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_char(user: User, db: AsyncSession) -> Character:
    res = await db.execute(select(Character).where(Character.user_id == user.id))
    char = res.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


async def _get_active_event(db: AsyncSession) -> WorldEvent | None:
    """Vrátí aktuálně aktivní event (nebo None)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    res = await db.execute(
        select(WorldEvent)
        .where(WorldEvent.is_active == True, WorldEvent.ends_at > now)
        .order_by(WorldEvent.id.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def _get_or_create_contrib(
    event_id: int, char_id: int, db: AsyncSession
) -> WorldEventContrib:
    res = await db.execute(
        select(WorldEventContrib).where(
            WorldEventContrib.event_id == event_id,
            WorldEventContrib.character_id == char_id,
        )
    )
    contrib = res.scalar_one_or_none()
    if not contrib:
        contrib = WorldEventContrib(
            event_id=event_id,
            character_id=char_id,
            contribution=0,
            last_contrib_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(contrib)
        await db.flush()
    return contrib


# ── Veřejná pomocná funkce pro ostatní routery ───────────────────────────────

async def add_world_event_contribution(
    event_type: str,
    char_id: int,
    amount: int,
    db: AsyncSession,
) -> None:
    """
    Přidá příspěvek k aktuálnímu eventu daného typu.
    Voláno z quest.py, dungeon.py, boss.py — tiše selhává (nechceme narušit reward flow).
    """
    try:
        event = await _get_active_event(db)
        if not event or event.event_type != event_type:
            return

        contrib = await _get_or_create_contrib(event.id, char_id, db)
        contrib.contribution += amount
        contrib.last_contrib_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Aktualizuj globální progress
        event.current_progress += amount

        # Zkontroluj dokončení
        if not event.is_completed and event.current_progress >= event.goal:
            event.is_completed = True
            log.info("WorldEvent completed", extra={"data": {
                "event_id": event.id,
                "name": event.name,
                "progress": event.current_progress,
            }})

        # Pozn.: commit provede volající router
    except Exception as e:
        log.warning("WorldEvent contrib failed", extra={"data": {"error": str(e)}})


# ── GET /world-events/current ─────────────────────────────────────────────────

@router.get("/current")
async def get_current_event(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí aktuální world event, community progress a vlastní příspěvek."""
    event = await _get_active_event(db)

    if not event:
        return {"event": None, "message": "Žádný aktivní World Event."}

    char = await _get_char(current_user, db)

    # Vlastní příspěvek
    own_res = await db.execute(
        select(WorldEventContrib).where(
            WorldEventContrib.event_id == event.id,
            WorldEventContrib.character_id == char.id,
        )
    )
    own_contrib = own_res.scalar_one_or_none()
    own_amount = own_contrib.contribution if own_contrib else 0

    # Zda hráč již vybral odměnu
    claim_res = await db.execute(
        select(WorldEventClaim).where(
            WorldEventClaim.event_id == event.id,
            WorldEventClaim.character_id == char.id,
        )
    )
    claim = claim_res.scalar_one_or_none()

    # Top přispěvatelé (limit 10)
    top_res = await db.execute(
        select(WorldEventContrib, Character.name)
        .join(Character, Character.id == WorldEventContrib.character_id)
        .where(WorldEventContrib.event_id == event.id)
        .order_by(WorldEventContrib.contribution.desc())
        .limit(10)
    )
    top_rows = top_res.all()
    top_contributors = [
        {"name": name, "contribution": c.contribution}
        for c, name in top_rows
    ]

    # Celkový počet přispěvatelů
    count_res = await db.execute(
        select(func.count()).where(WorldEventContrib.event_id == event.id)
    )
    contributor_count = count_res.scalar() or 0

    return {
        "event": event.to_dict(),
        "own_contribution": own_amount,
        "is_claimed": claim is not None,
        "can_claim": event.is_completed and claim is None and own_amount > 0,
        "top_contributors": top_contributors,
        "contributor_count": contributor_count,
    }


# ── POST /world-events/claim ──────────────────────────────────────────────────

@router.post("/claim")
async def claim_event_reward(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vyzvednutí odměny za dokončený world event."""
    char = await _get_char(current_user, db)
    event = await _get_active_event(db)

    if not event:
        raise HTTPException(404, "Žádný aktivní World Event.")
    if not event.is_completed:
        raise HTTPException(400, "Event ještě není dokončen.")

    # Zkontroluj příspěvek
    own_res = await db.execute(
        select(WorldEventContrib).where(
            WorldEventContrib.event_id == event.id,
            WorldEventContrib.character_id == char.id,
        )
    )
    own_contrib = own_res.scalar_one_or_none()
    if not own_contrib or own_contrib.contribution <= 0:
        raise HTTPException(400, "Nepřispěl jsi k tomuto eventu.")

    # Zkontroluj zda již nevybral
    claim_res = await db.execute(
        select(WorldEventClaim).where(
            WorldEventClaim.event_id == event.id,
            WorldEventClaim.character_id == char.id,
        )
    )
    if claim_res.scalar_one_or_none():
        raise HTTPException(400, "Odměna již byla vybrána.")

    # Proporcionální gold odměna (minimum 100 G i za minimální příspěvek)
    contrib_ratio = min(1.0, own_contrib.contribution / max(1, event.goal))
    gold_reward = max(100, int(event.reward_gold * contrib_ratio))
    crystals_reward = event.reward_crystals  # crystaly dostane každý přispěvatel stejně

    # Aplikuj odměny
    char.gold += gold_reward
    from models.economy import log_gold
    await log_gold(db, char, gold_reward, GoldReason.QUEST_REWARD,
                   {"source": "world_event", "event_id": event.id, "event_name": event.name})

    if crystals_reward > 0:
        char.crystals = (char.crystals or 0) + crystals_reward
        await add_crystals(char.id, crystals_reward, f"world_event:{event.id}", db)

    # Titul (všichni přispěvatelé)
    if event.reward_title and not char.current_title:
        char.current_title = event.reward_title

    # Ulož claim
    claim = WorldEventClaim(
        event_id=event.id,
        character_id=char.id,
        claimed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        gold_received=gold_reward,
        crystals_received=crystals_reward,
    )
    db.add(claim)
    await db.commit()

    log.info("WorldEvent reward claimed", extra={"data": {
        "char": char.name, "event": event.name,
        "gold": gold_reward, "crystals": crystals_reward,
    }})

    return {
        "message": f"🌍 Odměna vybrána! +{gold_reward} G, +{crystals_reward} Crystalů",
        "gold_received": gold_reward,
        "crystals_received": crystals_reward,
        "awarded_title": event.reward_title,
        "own_contribution": own_contrib.contribution,
        "contrib_ratio_pct": round(contrib_ratio * 100, 1),
    }


# ── GET /world-events/history ─────────────────────────────────────────────────

@router.get("/history")
async def get_event_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí historii dokončených world eventů."""
    res = await db.execute(
        select(WorldEvent)
        .where(WorldEvent.is_completed == True)
        .order_by(WorldEvent.ends_at.desc())
        .limit(10)
    )
    events = res.scalars().all()
    return {"history": [e.to_dict() for e in events]}


# ── Interní: Ensure active event (voláno z lifespan) ─────────────────────────

async def ensure_active_world_event(db: AsyncSession | None = None) -> None:
    """Vytvoří nový world event pokud žádný není aktivní (round-robin z definic)."""
    own_db = db is None
    if own_db:
        db = AsyncSessionLocal()

    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        existing = await db.execute(
            select(WorldEvent).where(WorldEvent.is_active == True, WorldEvent.ends_at > now)
        )
        if existing.scalar_one_or_none():
            return  # Event již existuje

        # Zjisti kolik eventů proběhlo (round-robin výběr)
        count_res = await db.execute(select(func.count()).select_from(WorldEvent))
        count = count_res.scalar() or 0
        defn = WORLD_EVENT_DEFINITIONS[count % len(WORLD_EVENT_DEFINITIONS)]

        event = WorldEvent(
            name=defn["name"],
            description=defn["description"],
            event_type=defn["event_type"],
            goal=defn["goal"],
            current_progress=0,
            starts_at=now,
            ends_at=now + timedelta(days=defn["duration_days"]),
            is_active=True,
            is_completed=False,
            reward_gold=defn["reward_gold"],
            reward_crystals=defn["reward_crystals"],
            reward_title=defn.get("reward_title"),
        )
        db.add(event)
        await db.commit()
        log.info("WorldEvent created", extra={"data": {"name": event.name, "type": event.event_type}})
    finally:
        if own_db:
            await db.close()
