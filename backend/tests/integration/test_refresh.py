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
    return registered.json(), login.json()


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
    new_data = response.json()
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
    latest = rotated.json()["refresh_token"]

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
        "refresh_token": login.json()["refresh_token"],
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
async def test_refresh_without_version_is_rejected(client):
    user, _ = await _register_and_login(client, "noversion")
    forged = _encode({
        "sub": str(user["id"]),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    })

    response = await client.post("/auth/refresh", json={"refresh_token": forged})
    assert response.status_code == 401
