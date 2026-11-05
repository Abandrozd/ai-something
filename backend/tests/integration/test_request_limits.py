import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.main import app
from app.models.character import Character
from app.models.message import Message
from app.models.user import User
from app.request_limits import (
    LOGIN_IP_LIMIT,
    LOGIN_USERNAME_LIMIT,
    LOGIN_USERNAME_WINDOW_SECONDS,
    MAX_MESSAGE_LENGTH,
    MAX_PASSWORD_LENGTH,
    REFRESH_IP_LIMIT,
    REGISTER_IP_LIMIT,
    TOO_MANY_ATTEMPTS,
    password_too_long_detail,
)
from app.security import hash_password


async def _register(client, username, password="password123", email=None):
    response = await client.post("/users/", json={
        "username": username,
        "email": email or f"{username}@example.com",
        "password": password,
    })
    return response


async def _message_count(db_session):
    result = await db_session.execute(select(func.count(Message.id)))
    return result.scalar() or 0


@pytest.mark.asyncio
async def test_login_allows_several_mistypes_then_succeeds(client):
    created = await _register(client, "mistype")
    assert created.status_code == 201

    for _ in range(5):
        wrong = await client.post("/auth/login", data={
            "username": "mistype",
            "password": "not-the-password",
        })
        assert wrong.status_code == 401

    right = await client.post("/auth/login", data={
        "username": "mistype",
        "password": "password123",
    })
    assert right.status_code == 200
    assert right.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_username_limit_returns_429_before_another_verify(client, monkeypatch):
    created = await _register(client, "alice")
    assert created.status_code == 201
    checks = {"n": 0}

    def fake_verify(plain, hashed):
        checks["n"] += 1
        return False

    monkeypatch.setattr("app.routers.auth.verify_password", fake_verify)

    for _ in range(LOGIN_USERNAME_LIMIT):
        wrong = await client.post("/auth/login", data={
            "username": "alice",
            "password": "wrong-password",
        })
        assert wrong.status_code == 401

    blocked = await client.post("/auth/login", data={
        "username": "alice",
        "password": "wrong-password",
    })
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == TOO_MANY_ATTEMPTS
    assert blocked.headers["retry-after"] == str(LOGIN_USERNAME_WINDOW_SECONDS)
    assert checks["n"] == LOGIN_USERNAME_LIMIT

    other = await client.post("/auth/login", data={
        "username": "bob",
        "password": "wrong-password",
    })
    assert other.status_code == 401
    assert checks["n"] == LOGIN_USERNAME_LIMIT


@pytest.mark.asyncio
async def test_login_ip_limit_does_not_block_another_address_or_register(client, monkeypatch):
    def fail_verify(plain, hashed):
        raise AssertionError("verify_password was called")

    monkeypatch.setattr("app.routers.auth.verify_password", fail_verify)

    for i in range(LOGIN_IP_LIMIT):
        response = await client.post("/auth/login", data={
            "username": f"ipuser{i}",
            "password": "я" * (MAX_PASSWORD_LENGTH + 1),
        })
        assert response.status_code == 422
        assert str(MAX_PASSWORD_LENGTH) in response.text

    blocked = await client.post("/auth/login", data={
        "username": "ipuser-extra",
        "password": "password123",
    })
    assert blocked.status_code == 429

    transport = ASGITransport(app=app, client=("203.0.113.10", 123))
    async with AsyncClient(transport=transport, base_url="http://test") as other_ip:
        allowed = await other_ip.post("/auth/login", data={
            "username": "ipuser0",
            "password": "password123",
        })
    assert allowed.status_code == 401

    created = await _register(client, "afterlimit")
    assert created.status_code == 201
    refresh = await client.post("/auth/refresh", json={"refresh_token": "nope"})
    assert refresh.status_code == 401


@pytest.mark.asyncio
async def test_oversized_login_password_is_rejected_before_verify(client, monkeypatch):
    created = await _register(client, "longlogin", password="password123")
    assert created.status_code == 201

    def fail_verify(plain, hashed):
        raise AssertionError("verify_password was called")

    monkeypatch.setattr("app.routers.auth.verify_password", fail_verify)
    response = await client.post("/auth/login", data={
        "username": "longlogin",
        "password": "я" * (MAX_PASSWORD_LENGTH + 1),
    })
    assert response.status_code == 422
    assert response.json()["detail"] == password_too_long_detail()


@pytest.mark.asyncio
async def test_password_at_max_length_can_register_and_log_in(client):
    password = "я" * MAX_PASSWORD_LENGTH
    created = await _register(client, "maxlen", password=password)
    assert created.status_code == 201

    logged_in = await client.post("/auth/login", data={
        "username": "maxlen",
        "password": password,
    })
    assert logged_in.status_code == 200


@pytest.mark.asyncio
async def test_register_keeps_minimum_and_rejects_huge_password_before_hash(
    client, monkeypatch,
):
    def fail_hash(password):
        raise AssertionError("hash_password was called")

    monkeypatch.setattr("app.services.user_service.hash_password", fail_hash)

    short = await _register(client, "shortpw", password="12345")
    assert short.status_code == 422
    assert "6" in short.text

    huge = await _register(client, "hugepw", password="я" * (MAX_PASSWORD_LENGTH + 1))
    assert huge.status_code == 422
    assert str(MAX_PASSWORD_LENGTH) in huge.text


@pytest.mark.asyncio
async def test_register_limit_returns_429_before_another_hash(client, monkeypatch, db_session):
    stored = hash_password("password123")
    hashes = {"n": 0}

    def fake_hash(password):
        hashes["n"] += 1
        return stored

    monkeypatch.setattr("app.services.user_service.hash_password", fake_hash)

    for i in range(REGISTER_IP_LIMIT):
        created = await _register(client, f"reg{i}")
        assert created.status_code == 201, created.text

    blocked = await _register(client, "reg-blocked")
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == TOO_MANY_ATTEMPTS
    assert hashes["n"] == REGISTER_IP_LIMIT

    saved = await db_session.execute(select(User).where(User.username == "reg-blocked"))
    assert saved.scalar_one_or_none() is None

    logged_in = await client.post("/auth/login", data={
        "username": "reg0",
        "password": "password123",
    })
    assert logged_in.status_code == 200


@pytest.mark.asyncio
async def test_refresh_limit_returns_429(client):
    for _ in range(REFRESH_IP_LIMIT):
        response = await client.post("/auth/refresh", json={"refresh_token": "nope"})
        assert response.status_code == 401

    blocked = await client.post("/auth/refresh", json={"refresh_token": "nope"})
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == TOO_MANY_ATTEMPTS


@pytest.mark.asyncio
async def test_change_password_rejects_huge_values_before_hash(client, monkeypatch):
    created = await _register(client, "pwchange")
    assert created.status_code == 201
    login = await client.post("/auth/login", data={
        "username": "pwchange",
        "password": "password123",
    })
    headers = {"Authorization": f"Bearer {login.cookies['access_token']}"}

    def fail_verify(plain, hashed):
        raise AssertionError("verify_password was called")

    def fail_hash(password):
        raise AssertionError("hash_password was called")

    monkeypatch.setattr("app.security.verify_password", fail_verify)
    monkeypatch.setattr("app.services.user_service.hash_password", fail_hash)

    long_new = await client.post(
        "/users/change-password",
        json={"old_password": "password123", "new_password": "a" * (MAX_PASSWORD_LENGTH + 1)},
        headers=headers,
    )
    assert long_new.status_code == 422
    assert str(MAX_PASSWORD_LENGTH) in long_new.text

    long_old = await client.post(
        "/users/change-password",
        json={"old_password": "a" * (MAX_PASSWORD_LENGTH + 1), "new_password": "newpassword123"},
        headers=headers,
    )
    assert long_old.status_code == 422
    assert str(MAX_PASSWORD_LENGTH) in long_old.text


@pytest.mark.asyncio
async def test_change_password_keeps_minimum_and_accepts_max_length(client):
    created = await _register(client, "pwbounds")
    assert created.status_code == 201
    login = await client.post("/auth/login", data={
        "username": "pwbounds",
        "password": "password123",
    })
    headers = {"Authorization": f"Bearer {login.cookies['access_token']}"}

    short = await client.post(
        "/users/change-password",
        json={"old_password": "password123", "new_password": "12345"},
        headers=headers,
    )
    assert short.status_code == 400
    assert short.json()["detail"] == "Пароль должен быть не короче 6 символов"

    accepted = await client.post(
        "/users/change-password",
        json={"old_password": "password123", "new_password": "б" * MAX_PASSWORD_LENGTH},
        headers=headers,
    )
    assert accepted.status_code == 200


@pytest.mark.asyncio
async def test_oversized_chat_message_is_rejected_before_the_model(
    client, db_session, mock_model,
):
    created = await _register(client, "bigchat")
    assert created.status_code == 201
    login = await client.post("/auth/login", data={
        "username": "bigchat",
        "password": "password123",
    })
    headers = {"Authorization": f"Bearer {login.cookies['access_token']}"}

    response = await client.post(
        "/chat/",
        json={"message": "a" * (MAX_MESSAGE_LENGTH + 1), "character_id": 1},
        headers=headers,
    )
    assert response.status_code == 422
    assert str(MAX_MESSAGE_LENGTH) in response.text
    assert mock_model["calls"] == []
    assert await _message_count(db_session) == 0


@pytest.mark.asyncio
async def test_chat_message_at_max_length_reaches_the_model(
    client, db_session, mock_model,
):
    created = await _register(client, "maxchat")
    assert created.status_code == 201
    login = await client.post("/auth/login", data={
        "username": "maxchat",
        "password": "password123",
    })
    headers = {"Authorization": f"Bearer {login.cookies['access_token']}"}
    character = Character(name="Bot", personality="Kind")
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)

    text = "a" * MAX_MESSAGE_LENGTH
    response = await client.post(
        "/chat/",
        json={"message": text, "character_id": character.id},
        headers=headers,
    )
    assert response.status_code == 200
    assert len(mock_model["calls"]) == 1
    assert mock_model["calls"][0]["messages"][-1]["content"] == text
