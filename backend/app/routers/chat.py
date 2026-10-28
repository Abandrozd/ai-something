from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.character import Character
from app.schemas.chat import ChatRequest
from app.config import get_settings

from openai import AsyncOpenAI

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
client = AsyncOpenAI(api_key=settings.API_KEY)


@router.post("/")
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    # Получаем или создаём пользователя
    result = await db.execute(select(User).where(User.username == "web_user"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(username="web_user")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Получаем или создаём диалог
    conversation = None
    if data.conversation_id:
        conversation = await db.get(Conversation, data.conversation_id)

    if not conversation:
        title = "New chat"
        if data.character_id:
            character = await db.get(Character, data.character_id)
            if character:
                title = character.name

        conversation = Conversation(
            user_id=user.id,
            character_id=data.character_id,
            title=title,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    # Сохраняем сообщение пользователя
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
    )
    db.add(user_msg)
    await db.commit()

    # Собираем историю
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.id)
    )
    messages = result.scalars().all()

    # Формируем промпт
    api_messages = []
    if conversation.character_id:
        character = await db.get(Character, conversation.character_id)
        if character:
            system_prompt = f"Ты — {character.name}. {character.personality or ''}"
            api_messages.append({"role": "system", "content": system_prompt})

    for m in messages:
        api_messages.append({"role": m.role, "content": m.content})

    # Стриминг ответа
    async def generate():
        full_response = ""
        stream = await client.chat.completions.create(
            model=settings.MODEL,
            messages=api_messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        # Сохраняем ответ ассистента
        ai_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
        )
        db.add(ai_msg)
        await db.commit()

    return StreamingResponse(generate(), media_type="text/plain")