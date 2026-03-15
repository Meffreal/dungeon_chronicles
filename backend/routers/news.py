"""
routers/news.py — In-game news feed

Public:
  GET /news/current — aktuální aktivní zprávy (ne starší než 14 dní)

Admin (vyžaduje X-Admin-Key header):
  GET  /admin/news          — všechny zprávy
  POST /admin/news          — vytvoř zprávu
  PUT  /admin/news/{id}     — update zprávy
  DELETE /admin/news/{id}   — smaž zprávu
"""
from datetime import datetime, timezone, timedelta

import os

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.news import GameNews

router = APIRouter(tags=["news"])

_NEWS_MAX_AGE_DAYS = 14
_ADMIN_KEY = os.getenv("ADMIN_KEY", "dungeon-admin-2024")


# ── Veřejný endpoint ─────────────────────────────────────────────────────────

@router.get("/news/current")
async def get_current_news(db: AsyncSession = Depends(get_db)):
    """Vrátí aktivní zprávy ne starší než 14 dní."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=_NEWS_MAX_AGE_DAYS)

    q = (
        select(GameNews)
        .where(GameNews.is_active == True)
        .where(GameNews.published_at >= cutoff)
        .where(
            (GameNews.expires_at == None) | (GameNews.expires_at >= now)
        )
        .order_by(GameNews.published_at.desc())
    )
    result = await db.execute(q)
    items = result.scalars().all()
    return [n.to_dict() for n in items]


# ── Admin helpers ─────────────────────────────────────────────────────────────

def _require_admin(x_admin_key: str | None = Header(default=None)):
    if x_admin_key != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


class NewsCreate(BaseModel):
    title:      str
    body:       str
    news_type:  str = "info"
    expires_at: str | None = None   # ISO datetime string nebo None
    author:     str | None = None


class NewsUpdate(BaseModel):
    title:      str | None = None
    body:       str | None = None
    news_type:  str | None = None
    is_active:  bool | None = None
    expires_at: str | None = None
    author:     str | None = None


# ── Admin endpointy ───────────────────────────────────────────────────────────

@router.get("/admin/news")
async def admin_list_news(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    result = await db.execute(select(GameNews).order_by(GameNews.published_at.desc()))
    return [n.to_dict() for n in result.scalars().all()]


@router.post("/admin/news", status_code=201)
async def admin_create_news(
    payload: NewsCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    expires = None
    if payload.expires_at:
        try:
            expires = datetime.fromisoformat(payload.expires_at.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Neplatný formát expires_at")

    news = GameNews(
        title=payload.title[:120],
        body=payload.body,
        news_type=payload.news_type,
        expires_at=expires,
        author=payload.author,
    )
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return news.to_dict()


@router.put("/admin/news/{news_id}")
async def admin_update_news(
    news_id: int,
    payload: NewsUpdate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    news = await db.get(GameNews, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Zpráva nenalezena")

    if payload.title is not None:
        news.title = payload.title[:120]
    if payload.body is not None:
        news.body = payload.body
    if payload.news_type is not None:
        news.news_type = payload.news_type
    if payload.is_active is not None:
        news.is_active = payload.is_active
    if payload.author is not None:
        news.author = payload.author
    if payload.expires_at is not None:
        try:
            news.expires_at = datetime.fromisoformat(
                payload.expires_at.replace("Z", "+00:00")
            ).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=400, detail="Neplatný formát expires_at")

    await db.commit()
    await db.refresh(news)
    return news.to_dict()


@router.delete("/admin/news/{news_id}")
async def admin_delete_news(
    news_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_require_admin),
):
    news = await db.get(GameNews, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="Zpráva nenalezena")
    await db.delete(news)
    await db.commit()
    return {"ok": True}
