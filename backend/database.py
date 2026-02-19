"""
database.py — SQLAlchemy async setup
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dungeon.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Migrace: seznam (tabulka, sloupec, definice) — přidá chybějící sloupce
_MIGRATIONS = [
    ("characters", "quests_completed", "INTEGER NOT NULL DEFAULT 0"),
    ("characters", "arena_cooldown_until", "DATETIME"),
    ("characters", "stat_points", "INTEGER NOT NULL DEFAULT 0"),
]

async def init_db():
    """Vytvoří všechny tabulky při startu a spustí migrace."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Postupné ALTER TABLE migrace (SQLite ignoruje duplicate column error)
        for table, column, definition in _MIGRATIONS:
            try:
                await conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                )
            except Exception:
                pass  # sloupec již existuje
