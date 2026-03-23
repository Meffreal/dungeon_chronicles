"""Integration tests for boss dungeon endpoints."""
import pytest
from models.character import Character
from sqlalchemy import select


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register(client, username: str):
    resp = await client.post("/auth/register", json={
        "username": username,
        "email": f"{username}@test.cz",
        "password": "heslo123",
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _create_char(client, token: str, name: str, cls: str = "warrior"):
    resp = await client.post(
        "/character/create",
        json={"name": name, "cls": cls, "is_hardcore": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["character"]


async def _set_level(db, char_id: int, level: int):
    """Directly set character level in DB (bypasses XP requirements)."""
    res = await db.execute(select(Character).where(Character.id == char_id))
    c = res.scalar_one()
    c.level = level
    await db.commit()


# ── Auth tests (uses client fixture — no character needed) ────────────────────

async def test_boss_list_requires_auth(client):
    resp = await client.get("/dungeon/boss/list")
    assert resp.status_code == 401


async def test_boss_bosses_requires_auth(client):
    resp = await client.get("/dungeon/boss/bosses/tomb_of_forgotten")
    assert resp.status_code == 401


async def test_boss_fight_requires_auth(client):
    resp = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten", "boss_num": 1
    })
    assert resp.status_code == 401


async def test_boss_status_requires_auth(client):
    resp = await client.get("/dungeon/boss/status")
    assert resp.status_code == 401


# ── List endpoint ─────────────────────────────────────────────────────────────

async def test_boss_list_returns_three_dungeons(client_db):
    client, db = client_db
    token = await _register(client, "listuser")
    await _create_char(client, token, "ListHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/list", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["dungeons"]) == 3
    keys = {d["key"] for d in data["dungeons"]}
    assert "tomb_of_forgotten" in keys
    assert "fiery_depths" in keys
    assert "citadel_of_chaos" in keys


async def test_boss_list_dungeon_has_expected_fields(client_db):
    client, db = client_db
    token = await _register(client, "fieldsuser")
    await _create_char(client, token, "FieldsHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/list", headers=headers)
    assert resp.status_code == 200
    tomb = next(d for d in resp.json()["dungeons"] if d["key"] == "tomb_of_forgotten")
    assert "is_unlocked" in tomb
    assert "highest_boss" in tomb
    assert "total_bosses" in tomb
    assert tomb["total_bosses"] == 50


async def test_boss_list_tomb_locked_at_low_level(client_db):
    """Level 1 character must not have tomb unlocked."""
    client, db = client_db
    token = await _register(client, "lowlvluser")
    await _create_char(client, token, "LowHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/list", headers=headers)
    assert resp.status_code == 200
    tomb = next(d for d in resp.json()["dungeons"] if d["key"] == "tomb_of_forgotten")
    assert tomb["is_unlocked"] is False


async def test_boss_list_tomb_unlocked_at_level_8(client_db):
    """Level 8 character must have tomb unlocked."""
    client, db = client_db
    token = await _register(client, "lvl8user")
    char = await _create_char(client, token, "Level8Hero")
    await _set_level(db, char["id"], 8)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/list", headers=headers)
    assert resp.status_code == 200
    tomb = next(d for d in resp.json()["dungeons"] if d["key"] == "tomb_of_forgotten")
    assert tomb["is_unlocked"] is True


# ── Bosses list endpoint ───────────────────────────────────────────────────────

async def test_boss_bosses_list_returns_50(client_db):
    client, db = client_db
    token = await _register(client, "bosslistuser")
    await _create_char(client, token, "BossListHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/bosses/tomb_of_forgotten", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bosses"]) == 50
    assert data["bosses"][0]["num"] == 1
    assert data["bosses"][49]["num"] == 50


async def test_boss_bosses_invalid_dungeon(client_db):
    client, db = client_db
    token = await _register(client, "invaliddunguser")
    await _create_char(client, token, "InvalidDungHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/bosses/nonexistent_dungeon", headers=headers)
    assert resp.status_code == 404


# ── Fight endpoint ─────────────────────────────────────────────────────────────

async def test_fight_locked_dungeon_blocked(client_db):
    """Level 1 character cannot fight in a locked dungeon."""
    client, db = client_db
    token = await _register(client, "lockedfightuser")
    await _create_char(client, token, "LockedFightHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten",
        "boss_num": 1,
    }, headers=headers)
    assert resp.status_code == 400


async def test_fight_wrong_boss_num(client_db):
    """Fighting boss #5 before defeating boss #1 should fail."""
    client, db = client_db
    token = await _register(client, "wrongbossuser")
    char = await _create_char(client, token, "WrongBossHero")
    await _set_level(db, char["id"], 8)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten",
        "boss_num": 5,
    }, headers=headers)
    assert resp.status_code == 400


async def test_fight_boss_1_returns_result(client_db):
    client, db = client_db
    token = await _register(client, "fightuser")
    char = await _create_char(client, token, "FightHero")
    await _set_level(db, char["id"], 8)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten",
        "boss_num": 1,
    }, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] in ("victory", "defeat")
    assert "combat_log" in data
    assert "cooldown_until" in data


async def test_fight_invalid_dungeon_key(client_db):
    client, db = client_db
    token = await _register(client, "invaliddungfight")
    char = await _create_char(client, token, "InvalidDungFight")
    await _set_level(db, char["id"], 8)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "nonexistent_dungeon",
        "boss_num": 1,
    }, headers=headers)
    assert resp.status_code in (400, 404)


async def test_cooldown_enforced_after_fight(client_db):
    """After fighting boss 1, fighting again immediately should be blocked (cooldown)."""
    client, db = client_db
    token = await _register(client, "cooldownuser")
    char = await _create_char(client, token, "CooldownHero")
    await _set_level(db, char["id"], 8)
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten", "boss_num": 1,
    }, headers=headers)
    assert r1.status_code == 200

    # After the fight a cooldown is set regardless of win/loss.
    # Determine which boss to try next.
    won = r1.json()["result"] == "victory"
    next_boss = 2 if won else 1

    r2 = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten",
        "boss_num": next_boss,
    }, headers=headers)
    assert r2.status_code == 400


# ── Status endpoint ────────────────────────────────────────────────────────────

async def test_boss_status_endpoint(client_db):
    client, db = client_db
    token = await _register(client, "statususer")
    await _create_char(client, token, "StatusHero")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/dungeon/boss/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "on_cooldown" in data
    assert "progress" in data


async def test_boss_status_reflects_fight(client_db):
    """After a successful fight, status should show updated progress."""
    client, db = client_db
    token = await _register(client, "statusfightuser")
    char = await _create_char(client, token, "StatusFightHero")
    await _set_level(db, char["id"], 8)
    headers = {"Authorization": f"Bearer {token}"}

    # Get status before fight
    before = await client.get("/dungeon/boss/status", headers=headers)
    assert before.status_code == 200

    # Fight boss 1
    fight = await client.post("/dungeon/boss/fight", json={
        "dungeon_key": "tomb_of_forgotten", "boss_num": 1,
    }, headers=headers)
    assert fight.status_code == 200

    # Status should now show on_cooldown = True
    after = await client.get("/dungeon/boss/status", headers=headers)
    assert after.status_code == 200
    assert after.json()["on_cooldown"] is True
