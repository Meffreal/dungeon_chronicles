"""
tests/test_permadeath_cleanup.py — Integration testy pro permadeath cleanup
"""
import pytest
import pytest_asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register(client, username: str, email: str = None):
    resp = await client.post("/auth/register", json={
        "username": username,
        "email": email or f"{username}@test.cz",
        "password": "heslo123",
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _create_char(client, token: str, name: str, cls: str = "warrior"):
    resp = await client.post("/character/create",
                             json={"name": name, "cls": cls},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
    return resp.json()["character"]


async def _set_dead(db, char_id: int):
    """Nastaví is_dead=True přímo v DB (simulace permadeath v testu)."""
    from models.character import Character
    from sqlalchemy import select
    res = await db.execute(select(Character).where(Character.id == char_id))
    c = res.scalar_one()
    c.is_dead = True
    await db.commit()


# ── Testy: Arena ───────────────────────────────────────────────────────────────

async def test_dead_char_not_in_arena_opponents(client_db):
    """Mrtvá postava se nesmí objevit v seznamu soupeřů."""
    client, db = client_db

    token_a = await _register(client, "alive_fighter")
    token_b = await _register(client, "dead_fighter")

    char_a = await _create_char(client, token_a, "Živý")
    char_b = await _create_char(client, token_b, "Mrtvý")

    await _set_dead(db, char_b["id"])

    resp = await client.get("/arena/opponents",
                            headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 200
    opponent_ids = [o["id"] for o in resp.json()["opponents"]]
    assert char_b["id"] not in opponent_ids, "Mrtvá postava nesmí být v seznamu soupeřů"


async def test_dead_char_not_in_arena_leaderboard(client_db):
    """Mrtvá postava se nesmí zobrazit v arénovém leaderboardu."""
    from models.character import Character
    from sqlalchemy import select

    client, db = client_db

    token_b = await _register(client, "dead_lb_fighter")
    char_b = await _create_char(client, token_b, "MrtvýLB")

    # Nastav vysoký ELO a kill
    res = await db.execute(select(Character).where(Character.id == char_b["id"]))
    b = res.scalar_one()
    b.arena_rank = 9999
    await db.commit()
    await _set_dead(db, char_b["id"])

    # Smaž cache aby test viděl čerstvý dotaz
    from core.cache import cache as _cache
    await _cache.delete("arena:leaderboard")

    resp = await client.get("/arena/leaderboard")
    assert resp.status_code == 200
    lb_names = [e["name"] for e in resp.json()]
    assert "MrtvýLB" not in lb_names, "Mrtvá postava nesmí být v leaderboardu"


async def test_dead_char_not_in_season_leaderboard(client_db):
    """Mrtvá postava se nesmí zobrazit v sezónním leaderboardu."""
    from models.character import Character
    from sqlalchemy import select

    client, db = client_db

    token_b = await _register(client, "dead_season_fighter")
    char_b = await _create_char(client, token_b, "MrtvýSezóna")

    res = await db.execute(select(Character).where(Character.id == char_b["id"]))
    b = res.scalar_one()
    b.arena_rank = 8888
    await db.commit()
    await _set_dead(db, char_b["id"])

    from core.cache import cache as _cache
    await _cache.delete("arena:season_leaderboard")

    resp = await client.get("/arena/season/leaderboard")
    assert resp.status_code == 200
    names = [e["name"] for e in resp.json()]
    assert "MrtvýSezóna" not in names, "Mrtvá postava nesmí být v sezónním leaderboardu"


async def test_cannot_attack_dead_character(client_db):
    """Útok na mrtvou postavu musí vrátit 404."""
    client, db = client_db

    token_a = await _register(client, "attacker_live")
    token_b = await _register(client, "defender_dead")

    char_a = await _create_char(client, token_a, "Útočník")
    char_b = await _create_char(client, token_b, "MrtvýObránce")

    await _set_dead(db, char_b["id"])

    resp = await client.post(f"/arena/attack/{char_b['id']}",
                             headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 404, f"Očekáván 404, dostal {resp.status_code}"
