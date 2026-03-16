"""
routers/notifications.py — Herní notifikace
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from database import get_db
from models.user import User
from models.character import Character
from models.notification import Notification
from routers.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _get_char(user: User, db: AsyncSession) -> Character:
    result = await db.execute(select(Character).where(Character.user_id == user.id, Character.is_dead == False))
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(404, "Postava nenalezena.")
    return char


@router.get("/")
async def get_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vrátí posledních 30 notifikací."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(Notification)
        .where(Notification.character_id == char.id)
        .order_by(Notification.created_at.desc())
        .limit(30)
    )
    notifs = result.scalars().all()
    unread = sum(1 for n in notifs if not n.is_read)

    return {
        "notifications": [n.to_dict() for n in notifs],
        "unread": unread,
    }


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Označí všechny notifikace jako přečtené."""
    char = await _get_char(user, db)

    await db.execute(
        update(Notification)
        .where(
            Notification.character_id == char.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "Vše označeno jako přečteno."}


@router.post("/read/{notif_id}")
async def mark_read(
    notif_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Označí jednu notifikaci jako přečtenou."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.character_id == char.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(404, "Notifikace nenalezena.")

    notif.is_read = True
    await db.commit()
    return {"message": "OK"}


@router.delete("/clear")
async def clear_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Smaže všechny přečtené notifikace."""
    char = await _get_char(user, db)

    result = await db.execute(
        select(Notification).where(
            Notification.character_id == char.id,
            Notification.is_read == True,
        )
    )
    old_notifs = result.scalars().all()
    for n in old_notifs:
        await db.delete(n)
    await db.commit()

    return {"deleted": len(old_notifs)}
