"""
tests/conftest.py — Sdílené fixtures pro pytest
"""
import sys
import os

# Přidej backend/ do sys.path aby fungovaly importy
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest_asyncio
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

import database
from database import get_db
from main import app
from middleware.rate_limit import RateLimitMiddleware


@pytest_asyncio.fixture
async def client(tmp_path):
    """
    HTTP test klient s izolovanou SQLite databází.

    Tabulky vytváříme SYNCHRONNĚ (žádný event loop = žádné problémy
    s aiosqlite a pytest-asyncio event loop scope).
    Pro HTTP requesty používáme async engine přes override_get_db.
    Lifespan beží normálně ale inicializuje produkční DB (idempotentně).

    Rate limiting je v testech vypnut — sdílená app instance by jinak
    akumulovala requesty přes testy a způsobovala 429 odpovědi.
    """
    db_file = tmp_path / "test_dungeon.db"
    db_url_sync = f"sqlite:///{db_file}"
    db_url_async = f"sqlite+aiosqlite:///{db_file}"

    # ── 1. Vytvoř tabulky synchronně (bez asyncio) ──────────────────────────
    sync_engine = create_sync_engine(db_url_sync)
    database.Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    # ── 2. Async engine + session factory pro test requesty ──────────────────
    test_engine = create_async_engine(db_url_async)
    TestSession = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # ── 3. Bypass rate limiteru (sdílená instance, okna se hromadí přes testy)
    original_dispatch = RateLimitMiddleware.dispatch

    async def unlimited_dispatch(self, request, call_next):
        return await call_next(request)

    RateLimitMiddleware.dispatch = unlimited_dispatch

    # ── 4. HTTP klient (lifespan beží, ale používá produkční engine) ─────────
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    RateLimitMiddleware.dispatch = original_dispatch
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(tmp_path):
    """
    Izolovaná async DB session pro unit testy DB funkcí.
    Vytváří prázdnou in-memory SQLite s celým schématem.
    Vhodné pro testování functions jako get_disabled_quest_ids, try_acquire_cron_lock.
    """
    db_file = tmp_path / "unit_test.db"
    db_url_sync  = f"sqlite:///{db_file}"
    db_url_async = f"sqlite+aiosqlite:///{db_file}"

    sync_engine = create_sync_engine(db_url_sync)
    database.Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    test_engine  = create_async_engine(db_url_async)
    TestSession  = async_sessionmaker(test_engine, expire_on_commit=False)

    async with TestSession() as session:
        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture
async def registered_user(client):
    """Zaregistrovaný uživatel — vrátí (token, username)."""
    resp = await client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "heslo123",
    })
    assert resp.status_code == 201
    data = resp.json()
    return data["access_token"], data["username"]


@pytest_asyncio.fixture
async def client_db(tmp_path):
    """
    Kombinovaná fixture: HTTP klient + přímý DB session na STEJNÉ databázi.
    Používej pro testy kde potřebuješ HTTP volání I přímé DB mutace (např. is_dead=True).
    Vrací tuple (client, db_session).
    """
    db_file = tmp_path / "test_dungeon.db"
    db_url_sync  = f"sqlite:///{db_file}"
    db_url_async = f"sqlite+aiosqlite:///{db_file}"

    sync_engine = create_sync_engine(db_url_sync)
    database.Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    test_engine  = create_async_engine(db_url_async)
    TestSession  = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    original_dispatch = RateLimitMiddleware.dispatch

    async def unlimited_dispatch(self, request, call_next):
        return await call_next(request)

    RateLimitMiddleware.dispatch = unlimited_dispatch

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        async with TestSession() as session:
            yield ac, session

    RateLimitMiddleware.dispatch = original_dispatch
    app.dependency_overrides.clear()
    await test_engine.dispose()
