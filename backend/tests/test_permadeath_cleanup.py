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


# ── Testy: Guild ───────────────────────────────────────────────────────────────

async def _give_gold(db, char_id: int, amount: int = 1000):
    """Nastaví gold postavě přímo v DB."""
    from models.character import Character
    from sqlalchemy import select
    res = await db.execute(select(Character).where(Character.id == char_id))
    c = res.scalar_one()
    c.gold = amount
    await db.commit()


async def test_dead_member_not_shown_in_guild(client_db):
    """Mrtvý člen se nesmí zobrazit v seznamu členů cechu."""
    client, db = client_db

    token_l = await _register(client, "guild_leader_live")
    token_m = await _register(client, "guild_member_die")

    char_l = await _create_char(client, token_l, "Leader")
    char_m = await _create_char(client, token_m, "ČlenKteryUmre")

    await _give_gold(db, char_l["id"])

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
    client, db = client_db

    token_l = await _register(client, "guild_leader_count")
    token_m = await _register(client, "guild_member_count_die")

    char_lc = await _create_char(client, token_l, "LeaderCount")
    char_m = await _create_char(client, token_m, "ČlenCount")

    await _give_gold(db, char_lc["id"])

    resp = await client.post("/guild/create",
                             json={"name": "CountCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 201
    guild_id = resp.json()["guild"]["id"]

    resp = await client.post(f"/guild/join/{guild_id}",
                             headers={"Authorization": f"Bearer {token_m}"})
    assert resp.status_code == 200

    await _set_dead(db, char_m["id"])

    resp = await client.get("/guild/list")
    assert resp.status_code == 200
    guilds = resp.json()["guilds"]
    test_guild = next((g for g in guilds if g["id"] == guild_id), None)
    assert test_guild is not None
    assert test_guild["member_count"] == 1, \
        f"Čekal member_count=1, dostal {test_guild['member_count']}"


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

    char.is_dead = True
    char.died_at = datetime.now(timezone.utc).replace(tzinfo=None)

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

    await db.commit()


async def test_permadeath_removes_char_from_guild(client_db):
    """Po permadeath musí být guild_id=None."""
    from models.character import Character
    from sqlalchemy import select

    client, db = client_db

    token_l = await _register(client, "pd_leader_remove")
    token_m = await _register(client, "pd_member_die")

    char_l = await _create_char(client, token_l, "LeaderR")
    char_m = await _create_char(client, token_m, "ClenDie")

    await _give_gold(db, char_l["id"], 500)

    resp = await client.post("/guild/create",
                             json={"name": "PDCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 201
    guild_id = resp.json()["guild"]["id"]

    resp = await client.post(f"/guild/join/{guild_id}",
                             headers={"Authorization": f"Bearer {token_m}"})
    assert resp.status_code == 200

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

    await _give_gold(db, char_l["id"], 500)

    resp = await client.post("/guild/create",
                             json={"name": "SucCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 201
    guild_id = resp.json()["guild"]["id"]

    resp = await client.post(f"/guild/join/{guild_id}",
                             headers={"Authorization": f"Bearer {token_m1}"})
    assert resp.status_code == 200
    resp = await client.post(f"/guild/join/{guild_id}",
                             headers={"Authorization": f"Bearer {token_m2}"})
    assert resp.status_code == 200

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

    await _give_gold(db, char_l["id"], 500)

    resp = await client.post("/guild/create",
                             json={"name": "SoloCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token_l}"})
    assert resp.status_code == 201
    guild_id = resp.json()["guild"]["id"]

    await _simulate_permadeath_cleanup(db, char_l["id"])

    g_res = await db.execute(select(Guild).where(Guild.id == guild_id))
    guild = g_res.scalar_one()
    assert guild is not None, "Guild musí stále existovat"
    assert guild.leader_id == char_l["id"], \
        "leader_id musí zůstat jako owner marker"


# ── Testy: Auto-rejoin při vytvoření nové postavy ─────────────────────────────

async def test_new_char_autojoins_orphaned_guild(client_db):
    """Nová postava automaticky přebere osiřelý cech (kde mrtvá postava byla leader)."""
    from models.character import Character
    from models.guild import Guild
    from sqlalchemy import select

    client, db = client_db

    token = await _register(client, "rejoin_user")
    char1 = await _create_char(client, token, "PrvníHrdina")

    await _give_gold(db, char1["id"], 500)

    resp = await client.post("/guild/create",
                             json={"name": "RejoinCech", "description": "", "emblem": "🛡️"},
                             headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 201
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
