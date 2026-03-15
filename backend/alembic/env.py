"""
alembic/env.py — Konfigurace prostředí pro Alembic migrace.

Klíčové vlastnosti:
- Async engine (aiosqlite/asyncpg) → konvertuje na sync URL pro Alembic
- render_as_batch=True → umožňuje ALTER TABLE na SQLite (batch mode)
- Importuje všechny modely přes models/__init__.py → autogenerate vidí celé schema
- URL čte z DATABASE_URL env var (stejný zdroj jako database.py)
"""
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Přidáme backend/ do sys.path (env.py je v backend/alembic/) ────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Import Base + všechny modely (populate metadata pro autogenerate) ───────
from database import Base, DATABASE_URL  # noqa: E402

# Importujeme models/__init__.py — registruje všechny SQLAlchemy modely do Base
import models  # noqa: E402, F401

# Přidáme i modely, které nejsou v __init__.py
from models.world_boss import WorldBoss, BossParticipation  # noqa: E402, F401
from models.dungeon_run import DungeonRun  # noqa: E402, F401

# ── Alembic config objekt ───────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata všech modelů — základ pro autogenerate
target_metadata = Base.metadata


# ── Helper: async URL → sync URL ────────────────────────────────────────────
def make_sync_url(url: str) -> str:
    """
    Alembic potřebuje synchronní connection.
    Konvertuje async drivery:
      sqlite+aiosqlite:///  →  sqlite:///
      postgresql+asyncpg:// →  postgresql+psycopg2://
    """
    return (
        url
        .replace("sqlite+aiosqlite://", "sqlite://")
        .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    )


def _is_sqlite(url: str) -> bool:
    """render_as_batch je nutný jen pro SQLite (PostgreSQL ho nepodporuje)."""
    return url.startswith("sqlite")


# ── Offline režim (generování SQL skriptů bez DB spojení) ───────────────────
def run_migrations_offline() -> None:
    url = make_sync_url(DATABASE_URL)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite(url),  # Pouze pro SQLite
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online režim (přímé spuštění migrací proti DB) ──────────────────────────
def run_migrations_online() -> None:
    sync_url = make_sync_url(DATABASE_URL)

    # Přepíšeme URL z ini (záměrně prázdné) hodnotou z prostředí
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = sync_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_is_sqlite(sync_url),  # Pouze pro SQLite
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Vstupní bod ──────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
