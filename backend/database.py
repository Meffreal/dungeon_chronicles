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


def _alembic_cfg():
    from alembic.config import Config
    cfg = Config(str(Path(__file__).parent / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
    return cfg


def _run_alembic_upgrade() -> None:
    from alembic import command
    command.upgrade(_alembic_cfg(), "head")


def _stamp_alembic_head() -> None:
    """Označí aktuální schéma jako head bez spouštění migrací (fresh install)."""
    from alembic import command
    command.stamp(_alembic_cfg(), "head")


async def _postgres_has_alembic_version(conn) -> bool:
    from sqlalchemy import text
    result = await conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'alembic_version')"
    ))
    return result.scalar()


async def init_db():
    """
    Inicializace schématu:

    SQLite (dev):
      create_all + alembic upgrade head
      DB persistuje na disku, Alembic verze je uložena → funguje opakovaně.

    PostgreSQL (prod) — fresh install (žádná alembic_version tabulka):
      create_all vytvoří celé schéma → stamp head (migrace jsou "already applied").
      Žádný conflict s migracemi, které by duplicitně vytvářely tabulky.

    PostgreSQL (prod) — existující install:
      alembic upgrade head aplikuje jen nové migrace.
    """
    is_sqlite = DATABASE_URL.startswith("sqlite")

    if is_sqlite:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await asyncio.to_thread(_run_alembic_upgrade)
        return

    # PostgreSQL: detekuj fresh install
    async with engine.connect() as conn:
        fresh = not await _postgres_has_alembic_version(conn)

    if fresh:
        # Nová DB: vytvoř vše přes create_all, označ jako head
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await asyncio.to_thread(_stamp_alembic_head)
    else:
        # Existující DB: aplikuj jen nové migrace
        await asyncio.to_thread(_run_alembic_upgrade)
