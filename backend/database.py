"""
database.py — SQLAlchemy async setup
"""
import os
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dungeon.db")

# Render.com dodává postgresql:// nebo postgres:// — SQLAlchemy async potřebuje postgresql+asyncpg://
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://"):
    _raw_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

DATABASE_URL = _raw_url

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def _run_alembic_upgrade() -> None:
    """Spustí 'alembic upgrade head' synchronně (voláno z asyncio.to_thread)."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(str(Path(__file__).parent / "alembic.ini"))
    # Zajistíme správný working directory (backend/)
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
    command.upgrade(alembic_cfg, "head")


async def init_db():
    """Vytvoří tabulky pro nové instalace a spustí Alembic migrace."""
    # create_all je bezpečné opakovat — vytvoří jen chybějící tabulky (nové instalace)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Alembic upgrade head — aplikuje všechny pending migrace
    # asyncio.to_thread přenese synchronní Alembic do thread poolu
    await asyncio.to_thread(_run_alembic_upgrade)
