import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/users/", json={
        "username": "newuser",
        "email": "new@example.com",
        "password": "password123",
        "role": "guest",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/users/", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "password123",
        "role": "guest",
    })

    response = await client.post("/auth/login", data={
        "username": "loginuser",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data