"""
routers/account.py — GDPR: export dat, soft delete, anonymizace
"""
import random
import string
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from core.logging import get_logger
from models.user import User
from models.character import Character
from models.item import InventoryItem, Item
from models.economy import GoldTransaction
from models.arena import ArenaMatch, SeasonResult
from models.achievement import PlayerAchievement
from models.crystal import CrystalTransaction
from routers.auth import get_current_user

log = get_logger(__name__)
router = APIRouter(prefix="/account", tags=["account"])

DELETE_RETENTION_DAYS = 30


async def _get_char(user: User, db: AsyncSession) -> Character | None:
    res = await db.execute(select(Character).where(Character.user_id == user.id))
    return res.scalar_one_or_none()


def _dt_iso(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


# ── GET /account/status ───────────────────────────────────────────────────────

@router.get("/status")
async def account_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí stav účtu — pending deletion, anonymized, datum vytvoření."""
    delete_after = None
    if current_user.is_deleted and current_user.deleted_at:
        dt = current_user.deleted_at
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        delete_after = (dt + timedelta(days=DELETE_RETENTION_DAYS)).strftime("%Y-%m-%d")

    return {
        "username": current_user.username,
        "email": current_user.email if not current_user.anonymized else "***",
        "created_at": _dt_iso(current_user.created_at),
        "last_login": _dt_iso(current_user.last_login),
        "is_deleted": current_user.is_deleted,
        "delete_after": delete_after,
        "anonymized": current_user.anonymized,
    }


# ── GET /account/export ───────────────────────────────────────────────────────

@router.get("/export")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR data export — JSON dump všech dat hráče."""
    char = await _get_char(current_user, db)
    char_data = None

    if char:
        # Inventář
        inv_res = await db.execute(
            select(InventoryItem, Item)
            .join(Item, InventoryItem.item_id == Item.id)
            .where(InventoryItem.character_id == char.id)
        )
        inventory = [
            {
                "item_name": item.name,
                "item_type": item.item_type,
                "rarity": item.rarity,
                "quantity": inv.quantity,
                "upgrade_level": inv.upgrade_level,
                "durability": inv.durability,
            }
            for inv, item in inv_res.all()
        ]

        # Gold transakce
        gold_res = await db.execute(
            select(GoldTransaction)
            .where(GoldTransaction.character_id == char.id)
            .order_by(GoldTransaction.timestamp.desc())
        )
        gold_txs = [
            {
                "amount": tx.amount,
                "reason": tx.reason.value if hasattr(tx.reason, "value") else tx.reason,
                "balance_after": tx.balance_after,
                "timestamp": _dt_iso(tx.timestamp),
                "detail": tx.detail,
            }
            for tx in gold_res.scalars().all()
        ]

        # Crystal transakce
        crystal_res = await db.execute(
            select(CrystalTransaction)
            .where(CrystalTransaction.character_id == char.id)
            .order_by(CrystalTransaction.timestamp.desc())
        )
        crystal_txs = [
            {
                "amount": tx.amount,
                "reason": tx.reason,
                "balance_after": tx.balance_after,
                "timestamp": _dt_iso(tx.timestamp),
            }
            for tx in crystal_res.scalars().all()
        ]

        # Arena zápasy (posledních 500)
        arena_res = await db.execute(
            select(ArenaMatch)
            .where(
                (ArenaMatch.attacker_id == char.id) | (ArenaMatch.defender_id == char.id)
            )
            .order_by(ArenaMatch.played_at.desc())
            .limit(500)
        )
        arena_matches = [
            {
                "attacker_id": m.attacker_id,
                "defender_id": m.defender_id,
                "winner_id": m.winner_id,
                "attacker_elo_change": m.attacker_elo_change,
                "defender_elo_change": m.defender_elo_change,
                "played_at": _dt_iso(m.played_at),
            }
            for m in arena_res.scalars().all()
        ]

        # Achievementy
        ach_res = await db.execute(
            select(PlayerAchievement)
            .where(PlayerAchievement.character_id == char.id)
        )
        achievements = [
            {
                "achievement_id": a.achievement_id,
                "unlocked_at": _dt_iso(a.unlocked_at),
            }
            for a in ach_res.scalars().all()
        ]

        # Sezónní výsledky
        season_res = await db.execute(
            select(SeasonResult)
            .where(SeasonResult.character_id == char.id)
            .order_by(SeasonResult.season_id.desc())
        )
        seasons = [
            {
                "season_id": sr.season_id,
                "final_rank": sr.final_rank,
                "final_elo": sr.final_elo,
                "reward_gold": sr.reward_gold,
                "reward_title": sr.reward_title,
                "reward_frame": sr.reward_frame,
            }
            for sr in season_res.scalars().all()
        ]

        char_data = {
            "name": char.name,
            "class": char.cls,
            "level": char.level,
            "xp": char.xp,
            "gold": char.gold,
            "crystals": char.crystals,
            "stats": {
                "strength": char.strength,
                "dexterity": char.dexterity,
                "intelligence": char.intelligence,
                "endurance": char.endurance,
                "luck": char.luck,
                "hp_max": char.hp_max,
                "mp_max": char.mp_max,
                "atk": char.atk,
                "def": char.def_,
                "spd": char.spd,
            },
            "subclass": char.subclass,
            "prestige_level": char.prestige_level,
            "talent_t2_key": char.talent_t2_key,
            "faction": char.faction,
            "current_title": char.current_title,
            "quests_completed": char.quests_completed,
            "arena_rank": char.arena_rank,
            "arena_wins": char.arena_wins,
            "arena_losses": char.arena_losses,
            "created_at": _dt_iso(char.created_at),
            "inventory": inventory,
            "gold_transactions": gold_txs,
            "crystal_transactions": crystal_txs,
            "arena_matches": arena_matches,
            "achievements": achievements,
            "season_results": seasons,
        }

    return {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "username": current_user.username,
            "email": current_user.email,
            "created_at": _dt_iso(current_user.created_at),
            "last_login": _dt_iso(current_user.last_login),
        },
        "character": char_data,
    }


# ── POST /account/delete ──────────────────────────────────────────────────────

@router.post("/delete")
async def request_delete(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete — označí účet ke smazání. Data se natrvalo smažou za 30 dní."""
    if current_user.is_deleted:
        raise HTTPException(400, "Účet je již označen ke smazání.")

    current_user.is_deleted = True
    current_user.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    delete_after = datetime.now(timezone.utc) + timedelta(days=DELETE_RETENTION_DAYS)
    log.info("Account delete requested", extra={"data": {"user_id": current_user.id}})
    return {
        "message": f"Účet bude trvale smazán {delete_after.strftime('%Y-%m-%d')}. "
                   "Do té doby se můžeš přihlásit a smazání zrušit.",
        "delete_after": delete_after.strftime("%Y-%m-%d"),
    }


# ── POST /account/delete/cancel ───────────────────────────────────────────────

@router.post("/delete/cancel")
async def cancel_delete(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zruší pending smazání účtu (dostupné do 30 dní od požadavku)."""
    if not current_user.is_deleted:
        raise HTTPException(400, "Účet není označen ke smazání.")

    current_user.is_deleted = False
    current_user.deleted_at = None
    await db.commit()

    log.info("Account delete cancelled", extra={"data": {"user_id": current_user.id}})
    return {"message": "Smazání účtu bylo zrušeno. Vše je v pořádku."}


# ── POST /account/anonymize ───────────────────────────────────────────────────

@router.post("/anonymize")
async def anonymize_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """GDPR right-to-erasure — anonymizuje email a vzhled postavy, zachová herní data."""
    if current_user.anonymized:
        raise HTTPException(400, "Účet je již anonymizován.")

    rand_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    # Anonymize user email (username zůstane pro herní záznamy)
    current_user.email = f"anon_{rand_suffix}@deleted.invalid"
    current_user.anonymized = True

    # Anonymize character cosmetics + appearance
    char = await _get_char(current_user, db)
    if char:
        char.appearance_json = None
        char.current_title = None
        char.crystal_name_color = None
        char.crystal_portrait_frame = None
        char.season_portrait_frame = None
        char.prestige_portrait_frame = None

    await db.commit()

    log.info("Account anonymized", extra={"data": {"user_id": current_user.id}})
    return {
        "message": "Osobní data (email, vzhled) byla anonymizována. "
                   "Herní záznamy (level, skóre, arena) jsou zachovány pro integritu žebříčků."
    }
