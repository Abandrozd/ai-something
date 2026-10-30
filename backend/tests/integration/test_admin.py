import pytest

@pytest.mark.asyncio
async def test_admin_access_forbidden(client):
    # Регистрируем обычного пользователя
    await client.post("/users/", json={
        "username": "regular",
        "email": "regular@example.com",
        "password": "password123",
        "role": "guest",
    })

    login = await client.post("/auth/login", data={
        "username": "regular",
        "password": "password123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Пытаемся зайти в админку
    response = await client.get("/admin/users", headers=headers)
    assert response.status_code == 403

    response = await client.get("/admin/stats", headers=headers)
    assert response.status_code == 403