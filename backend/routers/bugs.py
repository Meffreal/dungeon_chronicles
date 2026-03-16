"""
routers/bugs.py — Bug reporty od hráčů
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from routers.auth import get_current_user
from models.user import User
from models.character import Character
from models.bug_report import BugReport

router = APIRouter(prefix="/bugs", tags=["bugs"])

DAILY_REPORT_LIMIT = 5


class BugReportCreate(BaseModel):
    title:        str            = Field(..., min_length=3, max_length=120)
    description:  str            = Field(..., min_length=10, max_length=2000)
    steps:        str | None     = Field(None, max_length=2000)
    severity:     str            = Field("minor", pattern="^(cosmetic|minor|critical)$")
    page_context: str | None     = Field(None, max_length=80)


@router.post("/report")
async def submit_bug_report(
    payload: BugReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Načti postavu
    char = (await db.execute(
        select(Character).where(Character.user_id == user.id, Character.is_dead == False)
    )).scalars().first()

    if not char:
        raise HTTPException(400, "Pro odeslání bug reportu musíš mít vytvořenou postavu.")

    # Rate limit: max DAILY_REPORT_LIMIT reportů za posledních 24h
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    count = (await db.execute(
        select(func.count(BugReport.id)).where(
            BugReport.character_id == char.id,
            BugReport.created_at >= since
        )
    )).scalar_one()
    if count >= DAILY_REPORT_LIMIT:
        raise HTTPException(429, f"Denní limit {DAILY_REPORT_LIMIT} reportů byl dosažen.")

    report = BugReport(
        character_id = char.id if char else None,
        title        = payload.title,
        description  = payload.description,
        steps        = payload.steps,
        severity     = payload.severity,
        page_context = payload.page_context,
        char_name    = char.name if char else None,
        char_level   = char.level if char else None,
        char_class   = char.cls if char else None,
        status       = "open",
    )
    db.add(report)
    await db.commit()
    return {"ok": True, "id": report.id}
