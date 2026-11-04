import pytest

from app.models.character import Character


@pytest.mark.asyncio
async def test_clear_conversation_history(client, db_session):
    character = Character(name="ClearBot", personality="Test")
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    character_id = character.id

    # Обычный пользователь
    await client.post("/users/", json={
        "username": "clearuser",
        "email": "clear@example.com",
        "password": "password123",
    })
    login = await client.post("/auth/login", data={
        "username": "clearuser",
        "password": "password123",
    })
    token = login.cookies["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Отправляем сообщение
    await client.post(
        "/chat/",
        json={"message": "Hello", "character_id": character_id},
        headers=headers,
    )

    # Получаем диалог
    convs = await client.get("/conversations/", headers=headers)
    conversation_id = convs.json()[0]["id"]

    # Проверяем, что сообщения есть
    messages = await client.get(f"/conversations/{conversation_id}/messages", headers=headers)
    assert len(messages.json()) > 0

    # Очищаем историю
    response = await client.delete(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert response.status_code == 200

    # Проверяем, что сообщений нет
    messages = await client.get(f"/conversations/{conversation_id}/messages", headers=headers)
    assert len(messages.json()) == 0