import pytest

from app.models.character import Character
from app.models.conversation import Conversation


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
    return created.json()["id"], {
        "Authorization": f"Bearer {login.cookies['access_token']}",
    }


async def seed_dialogues(db_session, user_id):
    character = Character(name="Lira", personality="Calm")
    db_session.add(character)
    await db_session.flush()
    titles = ("First", "Second", "Third")
    created = []
    for title in titles:
        conversation = Conversation(
            user_id=user_id,
            character_id=character.id,
            title=title,
        )
        db_session.add(conversation)
        await db_session.flush()
        created.append(conversation)
    await db_session.commit()
    ids = [conversation.id for conversation in created]
    db_session.expunge_all()
    return ids


def listed(response):
    assert response.status_code == 200, response.text
    return [(item["id"], item["title"], item["is_pinned"]) for item in response.json()]


@pytest.mark.asyncio
async def test_rename_persists_for_the_owner(client, db_session):
    owner_id, headers = await register_and_login(client, "renamer", "renamer@example.com")
    first_id, second_id, third_id = await seed_dialogues(db_session, owner_id)

    renamed = await client.patch(
        f"/conversations/{second_id}",
        json={"title": "  Evening walk  "},
        headers=headers,
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "Evening walk"
    assert renamed.json()["is_pinned"] is False
    assert renamed.json()["id"] == second_id

    again = await client.get("/conversations/", headers=headers)
    assert listed(again) == [
        (third_id, "Third", False),
        (second_id, "Evening walk", False),
        (first_id, "First", False),
    ]


@pytest.mark.asyncio
async def test_blank_or_long_title_is_rejected(client, db_session):
    owner_id, headers = await register_and_login(client, "blanktitle", "blanktitle@example.com")
    conversation_id, _, _ = await seed_dialogues(db_session, owner_id)

    blank = await client.patch(
        f"/conversations/{conversation_id}",
        json={"title": "   "},
        headers=headers,
    )
    assert blank.status_code == 422

    too_long = await client.patch(
        f"/conversations/{conversation_id}",
        json={"title": "x" * 256},
        headers=headers,
    )
    assert too_long.status_code == 422

    stored = await client.get("/conversations/", headers=headers)
    titles = {item["id"]: item["title"] for item in stored.json()}
    assert titles[conversation_id] == "First"


@pytest.mark.asyncio
async def test_cannot_rename_someone_elses_conversation(client, db_session):
    owner_id, owner_headers = await register_and_login(
        client, "titleowner", "titleowner@example.com"
    )
    _, stranger_headers = await register_and_login(
        client, "titlestranger", "titlestranger@example.com"
    )
    conversation_id, _, _ = await seed_dialogues(db_session, owner_id)

    denied = await client.patch(
        f"/conversations/{conversation_id}",
        json={"title": "Stolen"},
        headers=stranger_headers,
    )
    assert denied.status_code == 404
    assert denied.json()["detail"] == "Диалог не найден"

    stored = await client.get("/conversations/", headers=owner_headers)
    titles = {item["id"]: item["title"] for item in stored.json()}
    assert titles[conversation_id] == "First"
    stranger_list = await client.get("/conversations/", headers=stranger_headers)
    assert stranger_list.json() == []


@pytest.mark.asyncio
async def test_pin_stays_on_top_until_unpinned(client, db_session):
    owner_id, headers = await register_and_login(client, "pinner", "pinner@example.com")
    first_id, second_id, third_id = await seed_dialogues(db_session, owner_id)

    before = await client.get("/conversations/", headers=headers)
    assert [item[0] for item in listed(before)] == [third_id, second_id, first_id]

    pinned = await client.patch(
        f"/conversations/{first_id}",
        json={"is_pinned": True},
        headers=headers,
    )
    assert pinned.status_code == 200, pinned.text
    assert pinned.json()["is_pinned"] is True
    assert pinned.json()["title"] == "First"

    after_pin = await client.get("/conversations/", headers=headers)
    assert listed(after_pin) == [
        (first_id, "First", True),
        (third_id, "Third", False),
        (second_id, "Second", False),
    ]
    reloaded = await client.get("/conversations/", headers=headers)
    assert listed(reloaded) == listed(after_pin)

    unpinned = await client.patch(
        f"/conversations/{first_id}",
        json={"is_pinned": False},
        headers=headers,
    )
    assert unpinned.status_code == 200, unpinned.text
    assert unpinned.json()["is_pinned"] is False

    after_unpin = await client.get("/conversations/", headers=headers)
    assert listed(after_unpin) == [
        (third_id, "Third", False),
        (second_id, "Second", False),
        (first_id, "First", False),
    ]


@pytest.mark.asyncio
async def test_cannot_pin_someone_elses_conversation(client, db_session):
    owner_id, owner_headers = await register_and_login(
        client, "pinowner", "pinowner@example.com"
    )
    _, stranger_headers = await register_and_login(
        client, "pinstranger", "pinstranger@example.com"
    )
    conversation_id, _, _ = await seed_dialogues(db_session, owner_id)

    denied = await client.patch(
        f"/conversations/{conversation_id}",
        json={"is_pinned": True},
        headers=stranger_headers,
    )
    assert denied.status_code == 404
    assert denied.json()["detail"] == "Диалог не найден"

    stored = await client.get("/conversations/", headers=owner_headers)
    own = next(item for item in stored.json() if item["id"] == conversation_id)
    assert own["is_pinned"] is False
    assert own["title"] == "First"