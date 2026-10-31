import pytest


@pytest.mark.asyncio
async def test_create_character_forbidden(client):
    await client.post("/users/", json={
        "username": "noadmin",
        "email": "noadmin@example.com",
        "password": "password123",
        "role": "guest",
    })

    login = await client.post("/auth/login", data={
        "username": "noadmin",
        "password": "password123",
    })
    token = login.json()["access_token"]

    response = await client.post(
        "/characters/",
        json={
            "name": "TestChar",
            "description": "Test",
            "personality": "Kind",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403