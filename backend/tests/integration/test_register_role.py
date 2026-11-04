import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "legend", "expert", "wanderer", "guest"])
async def test_register_ignores_client_role(client, role):
    response = await client.post("/users/", json={
        "username": f"user_{role}",
        "email": f"{role}@example.com",
        "password": "password123",
        "role": role,
    })
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "guest"
    assert body["username"] == f"user_{role}"

    login = await client.post("/auth/login", data={
        "username": f"user_{role}",
        "password": "password123",
    })
    assert login.status_code == 200
    token = login.json()["access_token"]

    admin_response = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert admin_response.status_code == 403


@pytest.mark.asyncio
async def test_register_without_role_is_guest(client):
    response = await client.post("/users/", json={
        "username": "plainuser",
        "email": "plain@example.com",
        "password": "password123",
    })
    assert response.status_code == 201
    assert response.json()["role"] == "guest"
