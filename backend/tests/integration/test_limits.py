import pytest


@pytest.mark.asyncio
async def test_message_limit(client):
    # Создаём админа и персонажа
    await client.post("/users/", json={
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "password123",
        "role": "admin",
    })
    admin_login = await client.post("/auth/login", data={
        "username": "adminuser",
        "password": "password123",
    })
    admin_token = admin_login.json()["access_token"]

    char_response = await client.post(
        "/characters/",
        json={"name": "TestBot", "personality": "Helpful"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    character_id = char_response.json()["id"]

    # Регистрируем пользователя
    await client.post("/users/", json={
        "username": "limituser",
        "email": "limit@example.com",
        "password": "password123",
        "role": "guest",
    })
    login = await client.post("/auth/login", data={
        "username": "limituser",
        "password": "password123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Первое сообщение — создаёт диалог
    response = await client.post(
        "/chat/",
        json={"message": "First", "character_id": character_id},
        headers=headers,
    )
    assert response.status_code == 200

    # Получаем id диалога
    convs = await client.get("/conversations/", headers=headers)
    conversation_id = convs.json()[0]["id"]

    # Отправляем ещё 4 сообщения в тот же диалог
    for i in range(4):
        response = await client.post(
            "/chat/",
            json={
                "message": f"Message {i}",
                "conversation_id": conversation_id,
                "character_id": character_id,
            },
            headers=headers,
        )
        assert response.status_code != 429

    # 6-е сообщение должно вернуть 429
    response = await client.post(
        "/chat/",
        json={
            "message": "One more",
            "conversation_id": conversation_id,
            "character_id": character_id,
        },
        headers=headers,
    )
    assert response.status_code == 429