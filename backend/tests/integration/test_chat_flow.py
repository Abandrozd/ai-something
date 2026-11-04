import pytest
from sqlalchemy import func, select

from app.models.character import Character
from app.models.conversation import Conversation
from app.models.message import Message


async def register_and_login(client, username, email):
    created = await client.post("/users/", json={
        "username": username,
        "email": email,
        "password": "password123",
    })
    assert created.status_code == 201, created.text
    login = await client.post("/auth/login", data={
        "username": username,
        "password": "password123",
    })
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.cookies['access_token']}"}


async def add_character(db_session, **extra):
    character = Character(
        name=extra.pop("name", "Bot"),
        personality=extra.pop("personality", "Kind"),
        **extra,
    )
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    return character


async def conversation_count(db_session, user_id=None):
    query = select(func.count(Conversation.id))
    if user_id is not None:
        query = query.where(Conversation.user_id == user_id)
    result = await db_session.execute(query)
    return result.scalar() or 0


@pytest.mark.asyncio
async def test_message_without_character_is_rejected(client, db_session):
    headers = await register_and_login(client, "emptyuser", "empty@example.com")

    response = await client.post(
        "/chat/",
        json={"message": "Hello", "conversation_id": None, "character_id": None},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Не выбран персонаж"
    assert await conversation_count(db_session) == 0


@pytest.mark.asyncio
async def test_missing_character_is_not_found(client, db_session):
    headers = await register_and_login(client, "missingchar", "missingchar@example.com")

    response = await client.post(
        "/chat/",
        json={"message": "Hello", "character_id": 99999},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Персонаж не найден"
    assert await conversation_count(db_session) == 0


@pytest.mark.asyncio
async def test_missing_conversation_does_not_create_another(client, db_session):
    headers = await register_and_login(client, "missingconv", "missingconv@example.com")
    character = await add_character(db_session)

    response = await client.post(
        "/chat/",
        json={
            "message": "Hello",
            "conversation_id": 424242,
            "character_id": character.id,
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Диалог не найден"
    assert await conversation_count(db_session) == 0


@pytest.mark.asyncio
async def test_first_message_returns_id_and_stores_reply(client, db_session, mock_model):
    headers = await register_and_login(client, "chatuser", "chat@example.com")
    character = await add_character(
        db_session,
        name="Lira",
        personality="Calm",
        description="A long description",
        scenario="Rainy city",
        first_message="Hi there",
    )
    mock_model["chunks"] = ["Hello ", "there"]

    response = await client.post(
        "/chat/",
        json={"message": "Hi", "character_id": character.id},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["x-conversation-id"]
    assert response.text == "Hello there"
    conversation_id = int(response.headers["x-conversation-id"])

    stored = await client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert stored.status_code == 200
    assert stored.json() == [
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello there"},
    ]

    sent = mock_model["calls"][0]["messages"]
    assert sent[0] == {
        "role": "system",
        "content": "Ты — Lira. Calm\nОписание: A long description\nСценарий: Rainy city",
    }
    assert sent[1:] == [
        {"role": "assistant", "content": "Hi there"},
        {"role": "user", "content": "Hi"},
    ]

    follow = await client.post(
        "/chat/",
        json={
            "message": "Again",
            "conversation_id": conversation_id,
            "character_id": None,
        },
        headers=headers,
    )
    assert follow.status_code == 200
    assert int(follow.headers["x-conversation-id"]) == conversation_id
    assert await conversation_count(db_session) == 1


@pytest.mark.asyncio
async def test_other_users_conversation_stays_forbidden(client, db_session, mock_model):
    owner = await register_and_login(client, "owner", "owner@example.com")
    stranger = await register_and_login(client, "stranger", "stranger@example.com")
    character = await add_character(db_session, name="Owned")

    created = await client.post(
        "/chat/",
        json={"message": "Mine", "character_id": character.id},
        headers=owner,
    )
    conversation_id = int(created.headers["x-conversation-id"])

    denied = await client.post(
        "/chat/",
        json={"message": "Not mine", "conversation_id": conversation_id},
        headers=stranger,
    )
    assert denied.status_code == 403
    assert await conversation_count(db_session) == 1


@pytest.mark.asyncio
async def test_model_failure_is_not_saved_and_does_not_spend_limit(
    client, db_session, mock_model
):
    headers = await register_and_login(client, "failuser", "fail@example.com")
    character = await add_character(db_session, name="Strict")

    async def broken_stream():
        yield type("Chunk", (), {"choices": []})()
        raise RuntimeError("upstream closed")

    conversation_id = None
    for index in range(4):
        mock_model["error"] = None
        mock_model["factory"] = None
        mock_model["chunks"] = [f"ok-{index}"]
        response = await client.post(
            "/chat/",
            json={
                "message": f"Message {index}",
                "character_id": character.id,
                **({"conversation_id": conversation_id} if conversation_id else {}),
            },
            headers=headers,
        )
        assert response.status_code == 200, response.text
        conversation_id = int(response.headers["x-conversation-id"])

    mock_model["factory"] = broken_stream
    failed = await client.post(
        "/chat/",
        json={
            "message": "this one fails",
            "conversation_id": conversation_id,
            "character_id": character.id,
        },
        headers=headers,
    )
    assert failed.status_code == 502
    assert "text/plain" not in failed.headers["content-type"]
    assert failed.json()["detail"] == "Произошла ошибка при генерации ответа."
    assert "upstream closed" not in failed.text
    assert "this one fails" not in failed.text

    messages = await client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    body = messages.json()
    assert len(body) == 8
    assert all(item["content"] != "this one fails" for item in body)
    assert all("ошибка" not in item["content"].lower() for item in body)

    user_messages = await db_session.execute(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
            Message.role == "user",
        )
    )
    assert user_messages.scalar() == 4

    mock_model["error"] = None
    mock_model["factory"] = None
    mock_model["chunks"] = ["recovered"]
    recovered = await client.post(
        "/chat/",
        json={
            "message": "after failure",
            "conversation_id": conversation_id,
        },
        headers=headers,
    )
    assert recovered.status_code == 200
    assert recovered.text == "recovered"

    blocked = await client.post(
        "/chat/",
        json={
            "message": "over the limit",
            "conversation_id": conversation_id,
        },
        headers=headers,
    )
    assert blocked.status_code == 429
    assert await conversation_count(db_session) == 1


@pytest.mark.asyncio
async def test_prompt_without_optional_fields_stays_name_and_personality(
    client, db_session, mock_model
):
    headers = await register_and_login(client, "plainuser", "plain@example.com")
    character = await add_character(db_session, name="Plain", personality="Quiet")
    mock_model["chunks"] = ["ok"]

    response = await client.post(
        "/chat/",
        json={"message": "Hi", "character_id": character.id},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["x-conversation-id"]
    assert mock_model["calls"][0]["messages"] == [
        {"role": "system", "content": "Ты — Plain. Quiet"},
        {"role": "user", "content": "Hi"},
    ]


@pytest.mark.asyncio
async def test_greeting_is_stored_sent_and_restored_on_clear(
    client, db_session, mock_model
):
    headers = await register_and_login(client, "greetuser", "greet@example.com")
    character = await add_character(
        db_session,
        name="Nova",
        personality="Witty",
        description="A navigator",
        scenario="On a ship",
        first_message="Welcome aboard",
    )
    mock_model["chunks"] = ["Aye"]

    opened = await client.post(
        "/chat/",
        json={"message": "Hello", "character_id": character.id},
        headers=headers,
    )
    assert opened.status_code == 200, opened.text
    conversation_id = int(opened.headers["x-conversation-id"])

    sent = mock_model["calls"][0]["messages"]
    assert sent[0]["content"] == (
        "Ты — Nova. Witty\nОписание: A navigator\nСценарий: On a ship"
    )
    assert sent[1:] == [
        {"role": "assistant", "content": "Welcome aboard"},
        {"role": "user", "content": "Hello"},
    ]

    stored = await client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert stored.json() == [
        {"role": "assistant", "content": "Welcome aboard"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Aye"},
    ]

    cleared = await client.delete(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json() == {"ok": True}

    after_clear = await client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert after_clear.status_code == 200
    assert after_clear.json() == [
        {"role": "assistant", "content": "Welcome aboard"},
    ]

    mock_model["chunks"] = ["Still here"]
    again = await client.post(
        "/chat/",
        json={"message": "You there?", "conversation_id": conversation_id},
        headers=headers,
    )
    assert again.status_code == 200, again.text
    assert int(again.headers["x-conversation-id"]) == conversation_id
    follow = mock_model["calls"][1]["messages"]
    assert follow[0]["role"] == "system"
    assert "A navigator" in follow[0]["content"]
    assert "On a ship" in follow[0]["content"]
    assert follow[1:] == [
        {"role": "assistant", "content": "Welcome aboard"},
        {"role": "user", "content": "You there?"},
    ]

    reloaded = await client.get(
        f"/conversations/{conversation_id}/messages",
        headers=headers,
    )
    assert reloaded.json() == [
        {"role": "assistant", "content": "Welcome aboard"},
        {"role": "user", "content": "You there?"},
        {"role": "assistant", "content": "Still here"},
    ]
    greetings = [
        item for item in reloaded.json()
        if item["content"] == "Welcome aboard"
    ]
    assert len(greetings) == 1


@pytest.mark.asyncio
async def test_failed_turn_does_not_persist_greeting(client, db_session, mock_model):
    headers = await register_and_login(client, "greetfail", "greetfail@example.com")
    character = await add_character(
        db_session,
        first_message="Hello from the void",
        description="Unused",
        scenario="Unused scene",
    )
    mock_model["error"] = RuntimeError("openai down")

    response = await client.post(
        "/chat/",
        json={"message": "Hello", "character_id": character.id},
        headers=headers,
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Произошла ошибка при генерации ответа."
    assert await conversation_count(db_session) == 0
    stored_messages = await db_session.execute(select(func.count(Message.id)))
    assert stored_messages.scalar() == 0
    assert mock_model["calls"][0]["messages"][1] == {
        "role": "assistant",
        "content": "Hello from the void",
    }


@pytest.mark.asyncio
async def test_model_error_before_stream_creates_nothing(client, db_session, mock_model):
    headers = await register_and_login(client, "nostart", "nostart@example.com")
    character = await add_character(db_session)
    mock_model["error"] = RuntimeError("openai down")

    response = await client.post(
        "/chat/",
        json={"message": "Hello", "character_id": character.id},
        headers=headers,
    )

    assert response.status_code == 502
    assert await conversation_count(db_session) == 0
    stored_messages = await db_session.execute(select(func.count(Message.id)))
    assert stored_messages.scalar() == 0
