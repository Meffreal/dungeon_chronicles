# Permadeath — Arena & Guild cleanup — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mrtvé postavy (is_dead=True) se nesmí zobrazovat v aréně ani cechu; při permadeath se postava automaticky odebere z cechu a leadership se předá nejvyššímu živému členovi; při vytvoření nové postavy se automaticky převezme osiřelý cech.

**Architecture:** Čtyři nezávislé oblasti změn — arena queries, guild queries, permadeath hook, character creation. Žádná migrace schématu. Všechny změny jsou v routerech.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, pytest-asyncio, httpx AsyncClient, SQLite (testy)

**Spec:** `docs/superpowers/specs/2026-03-16-permadeath-arena-guild-cleanup-design.md`

---

## Soubory

| Soubor | Změna |
|--------|-------|
| `backend/tests/conftest.py` | Přidat fixture `client_db` (sdílená DB pro HTTP + přímý session) |
| `backend/tests/test_permadeath_cleanup.py` | Nový test soubor |
| `backend/routers/arena.py` | Přidat `is_dead == False` filtr do 4 queries |
| `backend/routers/guild.py` | Přidat `is_dead == False` do `_member_count`, `my_guild`, WS |
| `backend/routers/dungeon.py` | Guild cleanup blok v `_trigger_permadeath` |
| `backend/routers/character.py` | Auto-rejoin blok v `create_character` |

---

## Chunk 1: Sdílená fixture + Arena filtry

### Task 1: Přidej `client_db` fixture do conftest

**Files:**
- Modify: `backend/tests/conftest.py`

Problém: stávající `client` a `db_session` fixtures používají **různé SQLite soubory** (`test_dungeon.db` vs `unit_test.db`). Testy potřebují HTTP klient a přímý DB přístup na **stejné** databázi.

- [ ] **Step 1: Přidej `client_db` fixture na konec `conftest.py`**

```python
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
```

- [ ] **Step 2: Ověř, že existující testy stále fungují**

```bash
cd backend && pytest tests/ -v --tb=short -q
```

Očekáváno: všechny existující testy PASS (nová fixture nic nerozbíjí).

---

### Task 2: Testy pro arena filtry

**Files:**
- Create: `backend/tests/test_permadeath_cleanup.py`

- [ ] **Step 3: Napiš failing testy**

```python
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
```

- [ ] **Step 4: Spusť testy — ověř, že failují**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_dead_char_not_in_arena_opponents tests/test_permadeath_cleanup.py::test_dead_char_not_in_arena_leaderboard tests/test_permadeath_cleanup.py::test_dead_char_not_in_season_leaderboard tests/test_permadeath_cleanup.py::test_cannot_attack_dead_character -v
```

Očekáváno: FAIL (mrtvé postavy se zobrazují / útok projde).

---

### Task 3: Implementuj arena filtry

**Files:**
- Modify: `backend/routers/arena.py`

- [ ] **Step 5: Oprav `get_opponents` — oba dotazy**

V `get_opponents` (ř. ~88) první dotaz:
```python
result = await db.execute(
    select(Character).where(
        and_(
            Character.id != char.id,
            Character.arena_rank >= max(100, char.arena_rank - 300),
            Character.arena_rank <= char.arena_rank + 300,
        )
    ).order_by(Character.arena_rank.desc()).limit(10)
)
```
Nahraď za:
```python
result = await db.execute(
    select(Character).where(
        and_(
            Character.id != char.id,
            Character.is_dead == False,
            Character.arena_rank >= max(100, char.arena_rank - 300),
            Character.arena_rank <= char.arena_rank + 300,
        )
    ).order_by(Character.arena_rank.desc()).limit(10)
)
```

Druhý dotaz (fallback, ř. ~101):
```python
result2 = await db.execute(
    select(Character).where(Character.id != char.id)
    .order_by(Character.arena_rank.desc()).limit(10)
)
```
Nahraď za:
```python
result2 = await db.execute(
    select(Character).where(
        Character.id != char.id,
        Character.is_dead == False,
    ).order_by(Character.arena_rank.desc()).limit(10)
)
```

- [ ] **Step 6: Oprav `attack/{defender_id}` — načtení obránce**

Najdi (ř. ~181):
```python
def_res = await db.execute(select(Character).where(Character.id == defender_id))
defender = def_res.scalar_one_or_none()
if not defender:
    raise HTTPException(404, "Soupeř nenalezen.")
```
Nahraď za:
```python
def_res = await db.execute(
    select(Character).where(Character.id == defender_id, Character.is_dead == False)
)
defender = def_res.scalar_one_or_none()
if not defender:
    raise HTTPException(404, "Soupeř nenalezen.")
```

- [ ] **Step 7: Oprav `arena_leaderboard`**

Najdi (ř. ~404):
```python
result = await db.execute(
    select(Character)
    .order_by(Character.arena_rank.desc())
    .limit(20)
)
```
Nahraď za:
```python
result = await db.execute(
    select(Character)
    .where(Character.is_dead == False)
    .order_by(Character.arena_rank.desc())
    .limit(20)
)
```

- [ ] **Step 8: Oprav `season_leaderboard`**

Najdi (ř. ~449):
```python
result = await db.execute(
    select(Character)
    .where(Character.arena_rank > 0)
    .order_by(Character.arena_rank.desc())
    .limit(25)
)
```
Nahraď za:
```python
result = await db.execute(
    select(Character)
    .where(Character.arena_rank > 0, Character.is_dead == False)
    .order_by(Character.arena_rank.desc())
    .limit(25)
)
```

- [ ] **Step 9: Spusť arena testy**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_dead_char_not_in_arena_opponents tests/test_permadeath_cleanup.py::test_dead_char_not_in_arena_leaderboard tests/test_permadeath_cleanup.py::test_dead_char_not_in_season_leaderboard tests/test_permadeath_cleanup.py::test_cannot_attack_dead_character -v
```

Očekáváno: všechny 4 PASS.

- [ ] **Step 10: Celá test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Očekáváno: žádné nové selhání.

- [ ] **Step 11: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_permadeath_cleanup.py backend/routers/arena.py
git commit -m "fix: mrtvé postavy se nezobrazují v aréně (opponents, leaderboard, attack)"
```

---

## Chunk 2: Guild — filtry mrtvých postav

### Task 4: Testy pro guild filtry

**Files:**
- Modify: `backend/tests/test_permadeath_cleanup.py`

- [ ] **Step 1: Přidej guild testy na konec test souboru**

```python
# ── Testy: Guild ───────────────────────────────────────────────────────────────

async def test_dead_member_not_shown_in_guild(client_db):
    """Mrtvý člen se nesmí zobrazit v seznamu členů cechu."""
    client, db = client_db

    token_l = await _register(client, "guild_leader_live")
    token_m = await _register(client, "guild_member_die")

    char_l = await _create_char(client, token_l, "Leader")
    char_m = await _create_char(client, token_m, "ČlenKteryUmre")

    resp = await client.post("/guild/create",
                             json={"name": "TestCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 201
    guild_id = resp.json()["guild"]["id"]

    resp = await client.post(f"/guild/join/{guild_id}",
                             headers={"Authorization": f"Bearer {token_m}"})
    assert resp.status_code == 200

    await _set_dead(db, char_m["id"])

    resp = await client.get("/guild/my",
                            headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 200
    member_ids = [mem["id"] for mem in resp.json()["members"]]
    assert char_m["id"] not in member_ids, "Mrtvý člen nesmí být v seznamu členů"


async def test_dead_member_not_counted_in_guild_list(client_db):
    """Mrtvý člen se nesmí počítat do member_count v seznam cechů."""
    from models.character import Character
    from sqlalchemy import select

    client, db = client_db

    token_l = await _register(client, "guild_leader_count")
    token_m = await _register(client, "guild_member_count_die")

    await _create_char(client, token_l, "LeaderCount")
    char_m = await _create_char(client, token_m, "ČlenCount")

    resp = await client.post("/guild/create",
                             json={"name": "CountCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 201
    guild_id = resp.json()["guild"]["id"]

    await client.post(f"/guild/join/{guild_id}",
                      headers={"Authorization": f"Bearer {token_m}"})

    await _set_dead(db, char_m["id"])

    resp = await client.get("/guild/list")
    assert resp.status_code == 200
    guilds = resp.json()["guilds"]
    test_guild = next((g for g in guilds if g["id"] == guild_id), None)
    assert test_guild is not None
    assert test_guild["member_count"] == 1, \
        f"Čekal member_count=1, dostal {test_guild['member_count']}"
```

- [ ] **Step 2: Spusť testy — ověř, že failují**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_dead_member_not_shown_in_guild tests/test_permadeath_cleanup.py::test_dead_member_not_counted_in_guild_list -v
```

Očekáváno: FAIL.

---

### Task 5: Implementuj guild filtry

**Files:**
- Modify: `backend/routers/guild.py`

- [ ] **Step 3: Oprav `_member_count`**

Najdi (ř. ~81):
```python
async def _member_count(guild_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).where(Character.guild_id == guild_id)
    )
    return result.scalar_one()
```
Nahraď za:
```python
async def _member_count(guild_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Character.id)).select_from(Character).where(
            Character.guild_id == guild_id,
            Character.is_dead == False,
        )
    )
    return result.scalar_one()
```

- [ ] **Step 4: Oprav `my_guild` members query**

Najdi (ř. ~232):
```python
members_res = await db.execute(
    select(Character).where(Character.guild_id == guild.id).order_by(Character.level.desc())
)
```
Nahraď za:
```python
members_res = await db.execute(
    select(Character).where(
        Character.guild_id == guild.id,
        Character.is_dead == False,
    ).order_by(Character.level.desc())
)
```

- [ ] **Step 5: Oprav WebSocket auth — načtení postavy**

Najdi v `guild_websocket` (ř. ~646):
```python
char_res = await db.execute(select(Character).where(Character.user_id == user_id))
char = char_res.scalar_one_or_none()
if not char or char.guild_id != guild_id:
    await ws.close(code=4003, reason="Not in this guild")
    return
```
Nahraď za:
```python
char_res = await db.execute(
    select(Character).where(Character.user_id == user_id, Character.is_dead == False)
)
char = char_res.scalar_one_or_none()
if not char or char.guild_id != guild_id:
    await ws.close(code=4003, reason="Not in this guild")
    return
```

- [ ] **Step 6: Spusť guild testy**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_dead_member_not_shown_in_guild tests/test_permadeath_cleanup.py::test_dead_member_not_counted_in_guild_list -v
```

Očekáváno: oba PASS.

- [ ] **Step 7: Celá test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Očekáváno: žádné nové selhání.

- [ ] **Step 8: Commit**

```bash
git add backend/routers/guild.py backend/tests/test_permadeath_cleanup.py
git commit -m "fix: mrtvé postavy se nezobrazují v cechu (member list, member count, WS)"
```

---

## Chunk 3: Permadeath hook — guild cleanup a succession

### Task 6: Testy pro permadeath guild cleanup

**Files:**
- Modify: `backend/tests/test_permadeath_cleanup.py`

- [ ] **Step 1: Přidej testy pro guild cleanup**

```python
# ── Testy: Permadeath guild cleanup ───────────────────────────────────────────

async def _simulate_permadeath_cleanup(db, char_id: int):
    """
    Simuluje guild cleanup část _trigger_permadeath:
    - nastaví is_dead=True a guild_id=None
    - předá leadership nástupci (pokud existuje)
    Neobsahuje HoF/Bloodline logiku (ta patří do dungeon.py).
    """
    from models.character import Character
    from models.guild import Guild
    from sqlalchemy import select
    from datetime import datetime, timezone

    res = await db.execute(select(Character).where(Character.id == char_id))
    char = res.scalar_one()

    if char.guild_id is not None:
        g_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
        guild = g_res.scalar_one_or_none()
        if guild and guild.leader_id == char.id:
            succ_res = await db.execute(
                select(Character).where(
                    Character.guild_id == guild.id,
                    Character.is_dead == False,
                    Character.id != char.id,
                ).order_by(Character.level.desc()).limit(1)
            )
            successor = succ_res.scalar_one_or_none()
            if successor:
                guild.leader_id = successor.id
        char.guild_id = None

    char.is_dead = True
    char.died_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()


async def test_permadeath_removes_char_from_guild(client_db):
    """Po permadeath musí být guild_id=None."""
    from models.character import Character
    from sqlalchemy import select

    client, db = client_db

    token_l = await _register(client, "pd_leader_remove")
    token_m = await _register(client, "pd_member_die")

    char_l = await _create_char(client, token_l, "LeaderR")
    char_m = await _create_char(client, token_m, "ČlenDie")

    resp = await client.post("/guild/create",
                             json={"name": "PDCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    guild_id = resp.json()["guild"]["id"]

    await client.post(f"/guild/join/{guild_id}",
                      headers={"Authorization": f"Bearer {token_m}"})

    await _simulate_permadeath_cleanup(db, char_m["id"])

    res = await db.execute(select(Character).where(Character.id == char_m["id"]))
    dead = res.scalar_one()
    assert dead.is_dead is True
    assert dead.guild_id is None, "Po permadeath musí být guild_id=None"


async def test_permadeath_leader_succession_to_highest_level(client_db):
    """Leadership přejde na živého člena s nejvyšším levelem."""
    from models.character import Character
    from models.guild import Guild
    from sqlalchemy import select

    client, db = client_db

    token_l  = await _register(client, "pd_leader_suc")
    token_m1 = await _register(client, "pd_member_low")
    token_m2 = await _register(client, "pd_member_high")

    char_l  = await _create_char(client, token_l,  "LeaderSuc")
    char_m1 = await _create_char(client, token_m1, "LowLevel")
    char_m2 = await _create_char(client, token_m2, "HighLevel")

    resp = await client.post("/guild/create",
                             json={"name": "SucCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    guild_id = resp.json()["guild"]["id"]

    await client.post(f"/guild/join/{guild_id}",
                      headers={"Authorization": f"Bearer {token_m1}"})
    await client.post(f"/guild/join/{guild_id}",
                      headers={"Authorization": f"Bearer {token_m2}"})

    # Nastav levely přímo v DB
    res1 = await db.execute(select(Character).where(Character.id == char_m1["id"]))
    res1.scalar_one().level = 1
    res2 = await db.execute(select(Character).where(Character.id == char_m2["id"]))
    res2.scalar_one().level = 10
    await db.commit()

    await _simulate_permadeath_cleanup(db, char_l["id"])

    g_res = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = g_res.scalar_one()
    assert guild.leader_id == char_m2["id"], \
        f"Leader má být HighLevel ({char_m2['id']}), dostal {guild.leader_id}"


async def test_permadeath_solo_leader_guild_keeps_marker(client_db):
    """Pokud leader umře sám, guild.leader_id zůstane jako owner marker."""
    from models.guild import Guild
    from sqlalchemy import select

    client, db = client_db

    token_l = await _register(client, "pd_solo_leader")
    char_l  = await _create_char(client, token_l, "SoloLeader")

    resp = await client.post("/guild/create",
                             json={"name": "SoloCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    guild_id = resp.json()["guild"]["id"]

    await _simulate_permadeath_cleanup(db, char_l["id"])

    g_res = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = g_res.scalar_one()
    assert guild is not None, "Guild musí stále existovat"
    assert guild.leader_id == char_l["id"], \
        "leader_id musí zůstat jako owner marker"
```

- [ ] **Step 2: Spusť testy — ověř, že failují**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_permadeath_removes_char_from_guild tests/test_permadeath_cleanup.py::test_permadeath_leader_succession_to_highest_level tests/test_permadeath_cleanup.py::test_permadeath_solo_leader_guild_keeps_marker -v
```

Očekáváno: FAIL (cleanup logika ještě není v `_trigger_permadeath`).

---

### Task 7: Implementuj guild cleanup v `_trigger_permadeath`

**Files:**
- Modify: `backend/routers/dungeon.py`

- [ ] **Step 3: Zkontroluj importy v dungeon.py**

Ujisti se, že tyto importy existují na vrcholu souboru. Pokud chybí, přidej je:
```python
from models.guild import Guild
from models.notification import Notification, NotifType
```

- [ ] **Step 4: Přidej guild cleanup blok do `_trigger_permadeath`**

Vlož blok **bezprostředně před `return {...}`** — tj. po volání `await award_death_bloodline_xp(...)` (ř. ~117–123), NE hned za `db.add(hall_entry)` (ř. ~114). Pořadí v funkci: hall_entry → bloodline_xp → **guild cleanup** → return.

```python
    # ── Guild cleanup ─────────────────────────────────────────────────────────
    if char.guild_id is not None:
        g_res = await db.execute(select(Guild).where(Guild.id == char.guild_id))
        guild = g_res.scalar_one_or_none()
        if guild and guild.leader_id == char.id:
            succ_res = await db.execute(
                select(Character).where(
                    Character.guild_id == guild.id,
                    Character.is_dead == False,
                    Character.id != char.id,
                ).order_by(Character.level.desc()).limit(1)
            )
            successor = succ_res.scalar_one_or_none()
            if successor:
                guild.leader_id = successor.id
                db.add(Notification(
                    character_id=successor.id,
                    type=NotifType.SYSTEM,
                    title="⚜ Stal ses Guild Masterem!",
                    body=f"{char.name} padl v boji. Vedení cechu přechází na tebe.",
                ))
            # else: guild.leader_id zůstane jako owner marker
        char.guild_id = None
```

Poznámka: `Character` a `select` jsou již importovány v `dungeon.py`.

- [ ] **Step 5: Spusť permadeath testy**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_permadeath_removes_char_from_guild tests/test_permadeath_cleanup.py::test_permadeath_leader_succession_to_highest_level tests/test_permadeath_cleanup.py::test_permadeath_solo_leader_guild_keeps_marker -v
```

Očekáváno: všechny 3 PASS.

- [ ] **Step 6: Celá test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Očekáváno: žádné nové selhání.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/dungeon.py backend/tests/test_permadeath_cleanup.py
git commit -m "fix: permadeath odebere postavu z cechu a předá leadership nejvyššímu živému členovi"
```

---

## Chunk 4: Character creation — auto-rejoin osiřelého cechu

### Task 8: Testy pro auto-rejoin

**Files:**
- Modify: `backend/tests/test_permadeath_cleanup.py`

- [ ] **Step 1: Přidej testy pro auto-rejoin**

```python
# ── Testy: Auto-rejoin při vytvoření nové postavy ─────────────────────────────

async def test_new_char_autojoins_orphaned_guild(client_db):
    """Nová postava automaticky přebere osiřelý cech (kde mrtvá postava byla leader)."""
    from models.character import Character
    from models.guild import Guild
    from sqlalchemy import select

    client, db = client_db

    token = await _register(client, "rejoin_user")
    char1 = await _create_char(client, token, "PrvníHrdina")

    resp = await client.post("/guild/create",
                             json={"name": "RejoinCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token}"})
    guild_id = resp.json()["guild"]["id"]

    # Simuluj permadeath cleanup: is_dead=True, guild_id=None, guild.leader_id zůstane
    res = await db.execute(select(Character).where(Character.id == char1["id"]))
    c = res.scalar_one()
    c.is_dead = True
    c.guild_id = None
    # guild.leader_id zůstane ukazovat na char1 (owner marker)
    await db.commit()

    # Vytvoř novou postavu
    resp2 = await client.post("/character/create",
                              json={"name": "DruhýHrdina", "cls": "warrior"},
                              headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 201
    char2 = resp2.json()["character"]

    # Nová postava musí být v cechu a musí být leaderem
    g_res = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = g_res.scalar_one()
    assert guild.leader_id == char2["id"], \
        f"Nová postava má být leader, dostal leader_id={guild.leader_id}"

    c2_res = await db.execute(select(Character).where(Character.id == char2["id"]))
    c2 = c2_res.scalar_one()
    assert c2.guild_id == guild_id, \
        f"Nová postava má být v cechu {guild_id}, dostal guild_id={c2.guild_id}"


async def test_new_char_no_orphaned_guild_no_autojoin(client_db):
    """Pokud předchozí postava nebyla leader cechu, nová postava nevstupuje do cechu."""
    from models.character import Character
    from sqlalchemy import select

    client, db = client_db

    token = await _register(client, "norejoin_user")
    char1 = await _create_char(client, token, "BezCechuHrdina")

    # Zabij bez cechu
    res = await db.execute(select(Character).where(Character.id == char1["id"]))
    res.scalar_one().is_dead = True
    await db.commit()

    resp2 = await client.post("/character/create",
                              json={"name": "DruhýBezCechu", "cls": "mage"},
                              headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 201
    char2 = resp2.json()["character"]

    c2_res = await db.execute(select(Character).where(Character.id == char2["id"]))
    c2 = c2_res.scalar_one()
    assert c2.guild_id is None, "Postava bez osiřelého cechu nesmí dostat guild_id"
```

- [ ] **Step 2: Spusť testy — ověř, že failují**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_new_char_autojoins_orphaned_guild tests/test_permadeath_cleanup.py::test_new_char_no_orphaned_guild_no_autojoin -v
```

Očekáváno: `test_new_char_autojoins_orphaned_guild` FAIL, `test_new_char_no_orphaned_guild_no_autojoin` PASS.

---

### Task 9: Implementuj auto-rejoin v `create_character`

**Files:**
- Modify: `backend/routers/character.py`

- [ ] **Step 3: Přidej import Guild do character.py**

Na vrcholu `routers/character.py` najdi importy modelů. Přidej pokud chybí:
```python
from models.guild import Guild
```

- [ ] **Step 4: Vlož auto-rejoin blok do `create_character`**

V funkci `create_character`, najdi `await db.flush()`. Blok vlož IHNED za `flush()` (a za případný legacy item blok, ale PŘED `await db.commit()`):

```python
    # ── Auto-rejoin: nová postava přebere osiřelý cech ────────────────────────
    dead_res = await db.execute(
        select(Character).where(
            Character.user_id == user.id,
            Character.is_dead == True,
        ).order_by(Character.id.desc())
    )
    for dead_char in dead_res.scalars().all():
        orphan_res = await db.execute(
            select(Guild).where(Guild.leader_id == dead_char.id)
        )
        orphan_guild = orphan_res.scalar_one_or_none()
        if orphan_guild:
            char.guild_id = orphan_guild.id
            orphan_guild.leader_id = char.id
            break  # max jeden cech na uživatele
```

- [ ] **Step 5: Spusť auto-rejoin testy**

```bash
cd backend && pytest tests/test_permadeath_cleanup.py::test_new_char_autojoins_orphaned_guild tests/test_permadeath_cleanup.py::test_new_char_no_orphaned_guild_no_autojoin -v
```

Očekáváno: oba PASS.

- [ ] **Step 6: Kompletní test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Očekáváno: všechny testy PASS, žádná regrese.

- [ ] **Step 7: Závěrečný commit**

```bash
git add backend/routers/character.py backend/tests/test_permadeath_cleanup.py
git commit -m "fix: nová postava automaticky přebere osiřelý cech po permadeath leadera"
```
