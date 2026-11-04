import pytest
from sqlalchemy import func, select

from app.models.character import Character
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User, UserRole
from app.security import hash_password


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
    token = login.cookies["access_token"]

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


async def login(client, username, password="password123"):
    response = await client.post("/auth/login", data={
        "username": username,
        "password": password,
    })
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.cookies['access_token']}"}


@pytest.mark.asyncio
async def test_delete_character_without_chats(client, db_session):
    db_session.add(User(
        username="charadmin",
        email="charadmin@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.ADMIN,
        is_active=True,
    ))
    character = Character(name="Lonely", personality="Quiet")
    db_session.add(character)
    await db_session.commit()
    await db_session.refresh(character)
    headers = await login(client, "charadmin")

    response = await client.delete(f"/characters/{character.id}", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    missing = await client.get(f"/characters/{character.id}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_delete_character_removes_conversations_and_messages(client, db_session):
    admin = User(
        username="deleter",
        email="deleter@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    guest = User(
        username="chatter",
        email="chatter@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.GUEST,
        is_active=True,
    )
    doomed = Character(
        name="Doomed",
        description="goes away",
        personality="bold",
        scenario="dock",
        first_message="hey",
    )
    kept = Character(name="Kept", personality="calm")
    db_session.add_all([admin, guest, doomed, kept])
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(guest)
    await db_session.refresh(doomed)
    await db_session.refresh(kept)

    own_chat = Conversation(user_id=admin.id, character_id=doomed.id, title="Own")
    other_chat = Conversation(user_id=guest.id, character_id=doomed.id, title="Other")
    kept_chat = Conversation(user_id=guest.id, character_id=kept.id, title="Kept")
    db_session.add_all([own_chat, other_chat, kept_chat])
    await db_session.flush()
    db_session.add_all([
        Message(conversation_id=own_chat.id, role="assistant", content="hey"),
        Message(conversation_id=own_chat.id, role="user", content="hi"),
        Message(conversation_id=other_chat.id, role="user", content="yo"),
        Message(conversation_id=kept_chat.id, role="user", content="stay"),
    ])
    await db_session.commit()
    doomed_id = doomed.id
    kept_chat_id = kept_chat.id
    db_session.expunge_all()

    guest_headers = await login(client, "chatter")
    denied = await client.delete(f"/characters/{doomed_id}", headers=guest_headers)
    assert denied.status_code == 403

    admin_headers = await login(client, "deleter")
    response = await client.delete(f"/characters/{doomed_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    missing = await client.get(f"/characters/{doomed_id}")
    assert missing.status_code == 404
    listed = await client.get("/characters/")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Kept"]

    admin_chats = await client.get("/conversations/", headers=admin_headers)
    assert admin_chats.status_code == 200
    assert admin_chats.json() == []

    guest_chats = await client.get("/conversations/", headers=guest_headers)
    assert guest_chats.status_code == 200
    assert [item["id"] for item in guest_chats.json()] == [kept_chat_id]

    kept_messages = await client.get(
        f"/conversations/{kept_chat_id}/messages",
        headers=guest_headers,
    )
    assert kept_messages.status_code == 200
    assert kept_messages.json() == [{"role": "user", "content": "stay"}]

    db_session.expire_all()
    conversation_rows = await db_session.execute(select(func.count(Conversation.id)))
    message_rows = await db_session.execute(select(func.count(Message.id)))
    doomed_rows = await db_session.execute(
        select(func.count(Conversation.id)).where(
            Conversation.character_id == doomed_id
        )
    )
    assert conversation_rows.scalar() == 1
    assert message_rows.scalar() == 1
    assert doomed_rows.scalar() == 0