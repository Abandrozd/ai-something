from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.config import get_settings


async def _register_and_login(client, username="refreshuser"):
    registered = await client.post("/users/", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "password123",
        "role": "guest",
    })
    assert registered.status_code == 201

    login = await client.post("/auth/login", data={
        "username": username,
        "password": "password123",
    })
    assert login.status_code == 200
    return registered.json(), _session_tokens(login)


def _session_tokens(response) -> dict:
    body = response.text
    payload = response.json()
    access = response.cookies.get("access_token")
    refresh = response.cookies.get("refresh_token")
    assert access, response.headers
    assert refresh, response.headers
    assert "access_token" not in payload
    assert "refresh_token" not in payload
    assert access not in body
    assert refresh not in body
    return {"access_token": access, "refresh_token": refresh}


def _encode(claims: dict) -> str:
    settings = get_settings()
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.mark.asyncio
async def test_refresh_token(client):
    _, tokens = await _register_and_login(client)

    response = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert response.status_code == 200
    new_data = _session_tokens(response)
    assert "access_token" in new_data
    assert "refresh_token" in new_data

    me = await client.get("/users/me", headers={
        "Authorization": f"Bearer {new_data['access_token']}",
    })
    assert me.status_code == 200
    assert me.json()["username"] == "refreshuser"


@pytest.mark.asyncio
async def test_refresh_token_is_rejected_as_access_token(client):
    _, tokens = await _register_and_login(client, "refreshaccess")

    rejected = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['refresh_token']}",
    })
    assert rejected.status_code == 401

    allowed = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert allowed.status_code == 200
    assert allowed.json()["username"] == "refreshaccess"


@pytest.mark.asyncio
async def test_access_token_cannot_refresh(client):
    _, tokens = await _register_and_login(client, "accessrefresh")

    response = await client.post("/auth/refresh", json={
        "refresh_token": tokens["access_token"],
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected(client):
    user, tokens = await _register_and_login(client, "expiredaccess")
    expired = _encode({
        "sub": str(user["id"]),
        "role": "guest",
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    })

    response = await client.get("/users/me", headers={
        "Authorization": f"Bearer {expired}",
    })
    assert response.status_code == 401

    still_valid = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert still_valid.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    _, tokens = await _register_and_login(client, "logoutuser")
    rotated = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert rotated.status_code == 200
    latest = _session_tokens(rotated)["refresh_token"]

    logout = await client.post("/auth/logout", json={"refresh_token": latest})
    assert logout.status_code == 200

    old = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    new = await client.post("/auth/refresh", json={"refresh_token": latest})
    assert old.status_code == 401
    assert new.status_code == 401

    login = await client.post("/auth/login", data={
        "username": "logoutuser",
        "password": "password123",
    })
    assert login.status_code == 200
    again = await client.post("/auth/refresh", json={
        "refresh_token": _session_tokens(login)["refresh_token"],
    })
    assert again.status_code == 200


@pytest.mark.asyncio
async def test_logout_with_access_token_does_not_revoke(client):
    _, tokens = await _register_and_login(client, "logoutaccess")

    rejected = await client.post("/auth/logout", json={
        "refresh_token": tokens["access_token"],
    })
    assert rejected.status_code == 401

    refreshed = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert refreshed.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_access_token(client):
    _, tokens = await _register_and_login(client, "logoutaccessver")

    before = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert before.status_code == 200

    logout = await client.post("/auth/logout", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert logout.status_code == 200

    after = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert after.status_code == 401

    login = await client.post("/auth/login", data={
        "username": "logoutaccessver",
        "password": "password123",
    })
    assert login.status_code == 200
    fresh = await client.get("/users/me", headers={
        "Authorization": f"Bearer {_session_tokens(login)['access_token']}",
    })
    assert fresh.status_code == 200
    stale = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert stale.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotation_revokes_previous_refresh(client):
    _, tokens = await _register_and_login(client, "rotationuser")
    previous_refresh = tokens["refresh_token"]
    previous_access = tokens["access_token"]

    rotated = await client.post("/auth/refresh", json={
        "refresh_token": previous_refresh,
    })
    assert rotated.status_code == 200
    current = _session_tokens(rotated)

    reused = await client.post("/auth/refresh", json={
        "refresh_token": previous_refresh,
    })
    assert reused.status_code == 401

    stale_access = await client.get("/users/me", headers={
        "Authorization": f"Bearer {previous_access}",
    })
    assert stale_access.status_code == 401

    current_access = await client.get("/users/me", headers={
        "Authorization": f"Bearer {current['access_token']}",
    })
    assert current_access.status_code == 200

    rotated_again = await client.post("/auth/refresh", json={
        "refresh_token": current["refresh_token"],
    })
    assert rotated_again.status_code == 200
    latest = _session_tokens(rotated_again)

    stolen = await client.post("/auth/refresh", json={
        "refresh_token": current["refresh_token"],
    })
    assert stolen.status_code == 401

    latest_access = await client.get("/users/me", headers={
        "Authorization": f"Bearer {latest['access_token']}",
    })
    assert latest_access.status_code == 200


@pytest.mark.asyncio
async def test_change_password_revokes_access_and_refresh(client):
    _, tokens = await _register_and_login(client, "pwdrevoke")

    changed = await client.post(
        "/users/change-password",
        json={"old_password": "password123", "new_password": "newpassword123"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert changed.status_code == 200

    access = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert access.status_code == 401

    refresh = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert refresh.status_code == 401

    old_login = await client.post("/auth/login", data={
        "username": "pwdrevoke",
        "password": "password123",
    })
    assert old_login.status_code == 401

    new_login = await client.post("/auth/login", data={
        "username": "pwdrevoke",
        "password": "newpassword123",
    })
    assert new_login.status_code == 200
    me = await client.get("/users/me", headers={
        "Authorization": f"Bearer {_session_tokens(new_login)['access_token']}",
    })
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_failed_password_change_does_not_revoke_session(client):
    _, tokens = await _register_and_login(client, "pwdkeep")

    rejected = await client.post(
        "/users/change-password",
        json={"old_password": "wrong-password", "new_password": "newpassword123"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert rejected.status_code == 400

    me = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert me.status_code == 200

    refreshed = await client.post("/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert refreshed.status_code == 200


@pytest.mark.asyncio
async def test_access_token_with_wrong_version_is_rejected(client):
    user, tokens = await _register_and_login(client, "badversion")
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    forged = _encode({
        "sub": str(user["id"]),
        "role": "guest",
        "type": "access",
        "ver": 99,
        "exp": future,
    })
    missing = _encode({
        "sub": str(user["id"]),
        "role": "guest",
        "type": "access",
        "exp": future,
    })

    wrong = await client.get("/users/me", headers={
        "Authorization": f"Bearer {forged}",
    })
    absent = await client.get("/users/me", headers={
        "Authorization": f"Bearer {missing}",
    })
    ok = await client.get("/users/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}",
    })
    assert wrong.status_code == 401
    assert absent.status_code == 401
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_refresh_without_version_is_rejected(client):
    user, _ = await _register_and_login(client, "noversion")
    forged = _encode({
        "sub": str(user["id"]),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    })

    response = await client.post("/auth/refresh", json={"refresh_token": forged})
    assert response.status_code == 401
