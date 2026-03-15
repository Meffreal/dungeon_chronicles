"""
tests/test_disabled_quests.py — Async DB testy pro disabled quest systém

Testuje:
  - get_disabled_quest_ids() — vrátí set z DB
  - disable_quest() — přidá do DB, invaliduje cache
  - enable_quest() — odstraní z DB, invaliduje cache
  - Idempotentnost: dvojité disable/enable nezpůsobí chybu
  - Cache: druhé volání get_disabled_quest_ids() použije cache
"""
import time
import pytest
import models.disabled_quest as dq_module
from models.disabled_quest import (
    get_disabled_quest_ids,
    disable_quest,
    enable_quest,
    _invalidate_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Před každým testem invalidujeme globální cache."""
    _invalidate_cache()
    yield
    _invalidate_cache()


# ── Základní operace ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_disabled_empty(db_session):
    """Prázdná DB → prázdný set."""
    result = await get_disabled_quest_ids(db_session)
    assert result == set()


@pytest.mark.asyncio
async def test_disable_quest_adds_to_result(db_session):
    """Po disable_quest se quest ID objeví v get_disabled_quest_ids."""
    await disable_quest(42, db_session)
    result = await get_disabled_quest_ids(db_session)
    assert 42 in result


@pytest.mark.asyncio
async def test_disable_multiple_quests(db_session):
    """Více quest ID lze deaktivovat najednou."""
    for qid in (1, 5, 10, 99):
        await disable_quest(qid, db_session)

    result = await get_disabled_quest_ids(db_session)
    assert {1, 5, 10, 99}.issubset(result)


@pytest.mark.asyncio
async def test_enable_quest_removes_from_result(db_session):
    """enable_quest odstraní quest ID z výsledku."""
    await disable_quest(42, db_session)
    await enable_quest(42, db_session)
    result = await get_disabled_quest_ids(db_session)
    assert 42 not in result


@pytest.mark.asyncio
async def test_enable_nonexistent_quest_no_error(db_session):
    """enable_quest pro nedeaktivovaný quest nesmí hodit výjimku."""
    await enable_quest(9999, db_session)  # Neexistuje → tiché ignorování


@pytest.mark.asyncio
async def test_disable_quest_idempotent(db_session):
    """Dvojité volání disable_quest nezpůsobí chybu ani duplikát."""
    await disable_quest(7, db_session)
    await disable_quest(7, db_session)  # Druhé volání — nesmí selhat

    result = await get_disabled_quest_ids(db_session)
    assert 7 in result
    assert len([qid for qid in result if qid == 7]) == 1


@pytest.mark.asyncio
async def test_enable_after_disable_restore(db_session):
    """disable → enable → quest není deaktivovaný."""
    await disable_quest(3, db_session)
    await disable_quest(7, db_session)
    await enable_quest(3, db_session)

    result = await get_disabled_quest_ids(db_session)
    assert 3 not in result
    assert 7 in result


# ── Cache logika ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_populated_after_first_call(db_session):
    """Po prvním get_disabled_quest_ids() je cache plná."""
    assert dq_module._cache is None   # Cache je prázdná

    await disable_quest(1, db_session)
    await get_disabled_quest_ids(db_session)

    assert dq_module._cache is not None
    assert 1 in dq_module._cache


@pytest.mark.asyncio
async def test_disable_invalidates_cache(db_session):
    """disable_quest invaliduje cache."""
    await get_disabled_quest_ids(db_session)  # Naplní cache
    assert dq_module._cache is not None

    await disable_quest(55, db_session)
    assert dq_module._cache is None  # Cache invalidována


@pytest.mark.asyncio
async def test_enable_invalidates_cache(db_session):
    """enable_quest invaliduje cache."""
    await disable_quest(55, db_session)
    await get_disabled_quest_ids(db_session)  # Naplní cache
    assert dq_module._cache is not None

    await enable_quest(55, db_session)
    assert dq_module._cache is None  # Cache invalidována


@pytest.mark.asyncio
async def test_cache_is_used_within_ttl(db_session):
    """Druhé volání get_disabled_quest_ids v rámci TTL vrátí cached data."""
    await disable_quest(11, db_session)
    first_result  = await get_disabled_quest_ids(db_session)
    cache_at_save = dq_module._cache_at

    second_result = await get_disabled_quest_ids(db_session)
    assert first_result == second_result
    # cache_at se nezměnil — data z cache
    assert dq_module._cache_at == cache_at_save


@pytest.mark.asyncio
async def test_cache_expires_and_refreshes(db_session):
    """Po expiraci TTL se cache obnoví z DB."""
    await disable_quest(22, db_session)
    await get_disabled_quest_ids(db_session)

    # Simuluj exspiraci cache (nastavíme _cache_at do minulosti)
    dq_module._cache_at = 0.0

    # Cache obnovena — nové DB čtení
    result = await get_disabled_quest_ids(db_session)
    assert 22 in result


# ── Vrácený typ ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_returns_set(db_session):
    result = await get_disabled_quest_ids(db_session)
    assert isinstance(result, set)


@pytest.mark.asyncio
async def test_returns_set_of_ints(db_session):
    await disable_quest(123, db_session)
    result = await get_disabled_quest_ids(db_session)
    for item in result:
        assert isinstance(item, int)
