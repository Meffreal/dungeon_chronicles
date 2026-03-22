# backend/tests/test_playtest_dungeon.py
import pytest
import pytest_asyncio
import random
import json
from sqlalchemy import update
from game.playtest_dungeon import (
    generate_map, get_available_nodes, unlock_successors,
    roll_relics, PLAYTEST_DUNGEONS, RELIC_POOL,
)


def test_generate_map_has_required_node_types():
    mdata = generate_map("pt_tomb", char_level=10)
    types = [n["type"] for n in mdata["nodes"].values()]
    assert "boss"   in types
    assert "elite"  in types
    assert "rest"   in types
    assert "start"  in mdata["nodes"]
    assert "n_boss" in mdata["nodes"]


def test_generate_map_constraint_rest():
    """Every map must have at least one rest node."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "rest" in types, f"Missing rest node: {types}"


def test_generate_map_constraint_elite():
    """Every map must have at least one elite node."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "elite" in types, f"Missing elite node: {types}"


def test_available_nodes_initially_layer1():
    """After entering, only layer 1 nodes (n1a, n1b) are available."""
    mdata = generate_map("pt_tomb", char_level=10)
    available = get_available_nodes(mdata)
    assert set(available) == {"n1a", "n1b"}


def test_unlock_successors():
    mdata = generate_map("pt_tomb", char_level=10)
    mdata["nodes"]["n1a"]["status"] = "completed"
    unlock_successors(mdata, "n1a")
    available = get_available_nodes(mdata)
    # n1a edges: ["n1a", "n2a"] and ["n1a", "n2b"] — both n2a and n2b must unlock
    assert "n2a" in available and "n2b" in available


def test_roll_relics_no_duplicates():
    """roll_relics must not return relics the player already has."""
    existing = ["blood_stone", "stone_shield"]
    relics = roll_relics(existing, count=3)
    ids = [r["id"] for r in relics]
    assert "blood_stone"  not in ids
    assert "stone_shield" not in ids
    assert len(relics) == 3


def test_roll_relics_count():
    relics = roll_relics([], count=3)
    assert len(relics) == 3


def test_generate_map_constraint_event():
    """Every map must have at least one event node."""
    for _ in range(20):
        mdata = generate_map("pt_tomb", char_level=10)
        types = [n["type"] for n in mdata["nodes"].values()]
        assert "event" in types, f"Missing event node: {types}"


def test_all_dungeon_keys_valid():
    for key in ["pt_tomb", "pt_fiery", "pt_citadel"]:
        mdata = generate_map(key, char_level=15)
        assert "n_boss" in mdata["nodes"]


# ── Integration testy (HTTP endpoints) ────────────────────────────────────────

async def _register_and_char(client, level=1, hp=100):
    """Zaregistruje usera, vytvoří postavu, vrátí (token, char_id, headers)."""
    uname = f"pt_{random.randint(10000, 99999)}"
    r = await client.post("/auth/register", json={
        "username": uname,
        "email": f"{uname}@test.cz",
        "password": "testpass123",
    })
    assert r.status_code == 201, f"Register failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r2 = await client.post(
        "/character/create",
        json={"name": "TestHrdina", "cls": "warrior"},
        headers=headers,
    )
    assert r2.status_code in (200, 201), f"Char create failed: {r2.text}"
    char_id = r2.json()["character"]["id"]
    return token, char_id, headers


async def _boost_char(db, char_id, level=10, hp=200):
    """Nastav level a hp_max postavy přes DB (Character nemá hp_current)."""
    from models.character import Character
    await db.execute(
        update(Character)
        .where(Character.id == char_id)
        .values(level=level, hp_max=hp)
    )
    await db.commit()


@pytest.mark.asyncio
async def test_list_dungeons(client):
    """GET /playtest/dungeon/list vrací 3 dungeony."""
    _, _, headers = await _register_and_char(client)
    resp = await client.get("/playtest/dungeon/list", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "dungeons" in data
    keys = [d["key"] for d in data["dungeons"]]
    assert len(keys) == 3
    for expected in ("pt_tomb", "pt_fiery", "pt_citadel"):
        assert expected in keys


@pytest.mark.asyncio
async def test_status_no_run(client):
    """GET /playtest/dungeon/status vrátí run=None pokud žádný aktivní run."""
    _, _, headers = await _register_and_char(client)
    resp = await client.get("/playtest/dungeon/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["run"] is None


@pytest.mark.asyncio
async def test_enter_dungeon_and_status(client_db):
    """POST /enter vytvoří run, GET /status ho pak vrátí."""
    client, db = client_db
    _, char_id, headers = await _register_and_char(client)
    await _boost_char(db, char_id, level=10, hp=200)

    r = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r.status_code == 200, f"Enter failed: {r.text}"
    run = r.json()["run"]
    for key in ("id", "dungeon_key", "status", "map_data", "hp_current", "hp_max"):
        assert key in run, f"Chybí klíč '{key}' v run dict"
    assert run["status"] == "active"

    r2 = await client.get("/playtest/dungeon/status", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["run"] is not None


@pytest.mark.asyncio
async def test_cannot_enter_twice(client_db):
    """Druhý enter selže s 400 obsahující 'aktivní'."""
    client, db = client_db
    _, char_id, headers = await _register_and_char(client)
    await _boost_char(db, char_id, level=10, hp=200)

    r1 = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r1.status_code == 200

    r2 = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r2.status_code == 400
    assert "aktivní" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_choose_node_combat(client_db):
    """POST /choose-node na combat node vrátí 200."""
    client, db = client_db
    _, char_id, headers = await _register_and_char(client)
    await _boost_char(db, char_id, level=10, hp=500)

    r = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r.status_code == 200
    run = r.json()["run"]
    run_id = run["id"]

    raw = run["map_data"]
    map_data = raw if isinstance(raw, dict) else json.loads(raw)
    available = [
        nid for nid, n in map_data["nodes"].items()
        if n["status"] == "available" and n["type"] == "combat"
    ]
    if not available:
        pytest.skip("Žádný dostupný combat node v mapě")

    node_id = available[0]
    r2 = await client.post(
        "/playtest/dungeon/choose-node",
        json={"run_id": run_id, "node_id": node_id},
        headers=headers,
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_rest_node_heals(client_db):
    """POST /choose-node na rest node obnoví HP."""
    client, db = client_db
    _, char_id, headers = await _register_and_char(client)
    await _boost_char(db, char_id, level=10, hp=200)

    r = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r.status_code == 200
    run = r.json()["run"]
    run_id = run["id"]

    raw = run["map_data"]
    map_data = raw if isinstance(raw, dict) else json.loads(raw)
    rest_nodes = [
        nid for nid, n in map_data["nodes"].items()
        if n["status"] == "available" and n["type"] == "rest"
    ]
    if not rest_nodes:
        pytest.skip("Žádný dostupný rest node v počáteční vrstvě")

    # Sníž HP aby bylo co léčit — updatujeme run přímo v DB
    from models.playtest_run import PlaytestRun
    await db.execute(
        update(PlaytestRun)
        .where(PlaytestRun.id == run_id)
        .values(hp_current=100)
    )
    await db.commit()

    node_id = rest_nodes[0]
    r2 = await client.post(
        "/playtest/dungeon/choose-node",
        json={"run_id": run_id, "node_id": node_id},
        headers=headers,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["run"]["hp_current"] > 100


@pytest.mark.asyncio
async def test_collect_requires_completed_run(client_db):
    """POST /collect selže (404) pokud run není completed/failed."""
    client, db = client_db
    _, char_id, headers = await _register_and_char(client)
    await _boost_char(db, char_id, level=10, hp=200)

    r = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r.status_code == 200
    run_id = r.json()["run"]["id"]

    r2 = await client.post(
        "/playtest/dungeon/collect",
        json={"run_id": run_id},
        headers=headers,
    )
    # Run je stále "active" → endpoint vrátí 404 (žádný run "čeká na vyzvednutí")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_abandon_run(client_db):
    """POST /abandon změní status; GET /status pak vrátí run=None."""
    client, db = client_db
    _, char_id, headers = await _register_and_char(client)
    await _boost_char(db, char_id, level=10, hp=200)

    r = await client.post(
        "/playtest/dungeon/enter",
        json={"dungeon_key": "pt_tomb"},
        headers=headers,
    )
    assert r.status_code == 200
    run_id = r.json()["run"]["id"]

    r2 = await client.post(
        "/playtest/dungeon/abandon",
        json={"run_id": run_id},
        headers=headers,
    )
    assert r2.status_code == 200

    r3 = await client.get("/playtest/dungeon/status", headers=headers)
    assert r3.status_code == 200
    # Po abandon je status="failed" → /status vrátí None (hledá jen "active")
    assert r3.json()["run"] is None
