"""
tests/test_auth.py — Testy pro /auth/register, /auth/login, /auth/me
"""


async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "username": "novyhrac",
        "email": "hrac@test.cz",
        "password": "tajneheslo",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "novyhrac"
    assert data["has_character"] is False


async def test_register_duplicate_username(client):
    payload = {"username": "dupuser", "email": "dup1@test.cz", "password": "heslo123"}
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201

    payload2 = {"username": "dupuser", "email": "dup2@test.cz", "password": "heslo123"}
    r2 = await client.post("/auth/register", json=payload2)
    assert r2.status_code == 400


async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={
        "username": "user1", "email": "same@test.cz", "password": "heslo123",
    })
    resp = await client.post("/auth/register", json={
        "username": "user2", "email": "same@test.cz", "password": "heslo123",
    })
    assert resp.status_code == 400


async def test_register_short_password(client):
    resp = await client.post("/auth/register", json={
        "username": "kratkeheslo",
        "email": "short@test.cz",
        "password": "abc",   # < 6 znaků
    })
    assert resp.status_code == 422


async def test_register_invalid_username_chars(client):
    resp = await client.post("/auth/register", json={
        "username": "bad user!",   # mezera + vykřičník
        "email": "bad@test.cz",
        "password": "heslo123",
    })
    assert resp.status_code == 422


async def test_register_username_too_short(client):
    resp = await client.post("/auth/register", json={
        "username": "ab",   # < 3 znaky
        "email": "ab@test.cz",
        "password": "heslo123",
    })
    assert resp.status_code == 422


async def test_login_success(client, registered_user):
    _token, _username = registered_user
    resp = await client.post("/auth/login", data={
        "username": "testuser",
        "password": "heslo123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["has_character"] is False


async def test_login_wrong_password(client, registered_user):
    resp = await client.post("/auth/login", data={
        "username": "testuser",
        "password": "spatneheslo",
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(client):
    resp = await client.post("/auth/login", data={
        "username": "neexistuje",
        "password": "heslo123",
    })
    assert resp.status_code == 401


async def test_me_endpoint(client, registered_user):
    token, username = registered_user
    resp = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == username


async def test_me_unauthorized(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client):
    resp = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer tohle_neni_platny_token"},
    )
    assert resp.status_code == 401
