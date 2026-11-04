import pytest

from app.models.character import Character


@pytest.mark.asyncio
async def test_message_limit(client, db_session):
    character = Character(name="TestBot", personality="Helpful")
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    character_id = character.id

    # Регистрируем пользователя
    await client.post("/users/", json={
        "username": "limituser",
        "email": "limit@example.com",
        "password": "password123",
    })
    login = await client.post("/auth/login", data={
        "username": "limituser",
        "password": "password123",
    })
    token = login.cookies["access_token"]
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