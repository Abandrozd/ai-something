import pytest


@pytest.mark.asyncio
async def test_get_me(client):
    # Регистрация
    await client.post("/users/", json={
        "username": "meuser",
        "email": "me@example.com",
        "password": "password123",
        "role": "guest",
    })

    # Логин
    login = await client.post("/auth/login", data={
        "username": "meuser",
        "password": "password123",
    })
    token = login.json()["access_token"]

    # Получение профиля
    response = await client.get("/users/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    response = await client.get("/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_success(client):
    await client.post("/users/", json={
        "username": "pwduser",
        "email": "pwd@example.com",
        "password": "oldpassword",
        "role": "guest",
    })

    login = await client.post("/auth/login", data={
        "username": "pwduser",
        "password": "oldpassword",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/users/change-password",
        json={"old_password": "oldpassword", "new_password": "newpassword123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old(client):
    await client.post("/users/", json={
        "username": "pwduser2",
        "email": "pwd2@example.com",
        "password": "oldpassword",
        "role": "guest",
    })

    login = await client.post("/auth/login", data={
        "username": "pwduser2",
        "password": "oldpassword",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/users/change-password",
        json={"old_password": "wrong", "new_password": "newpassword123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400