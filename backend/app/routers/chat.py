from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.dependencies import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.character import Character
from app.schemas.chat import ChatRequest
from app.config import get_settings
from app.security import get_current_user
from app.logger import get_logger
from app.limits import get_message_limit
from openai import AsyncOpenAI

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
client = AsyncOpenAI(api_key=settings.API_KEY)


@router.post("/")
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),

):
    logger.info(
        "Сообщение от user_id=%s, conversation_id=%s, character_id=%s",
        current_user.id, data.conversation_id, data.character_id
    )

    # Получаем или создаём диалог
    conversation = None
    if data.conversation_id:
        conversation = await db.get(Conversation, data.conversation_id)
        if conversation and conversation.user_id != current_user.id:
            logger.warning(
                "Попытка доступа к чужому диалогу: user_id=%s, conversation_id=%s",
                current_user.id, data.conversation_id
            )
            raise HTTPException(status_code=403, detail="Нет доступа к этому диалогу")

    if not conversation:
        title = "New chat"
        if data.character_id:
            character = await db.get(Character, data.character_id)
            if character:
                title = character.name

        conversation = Conversation(
            user_id=current_user.id,
            character_id=data.character_id,
            title=title,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        logger.info(
            "Создан новый диалог id=%s для user_id=%s (персонаж: %s)",
            conversation.id, current_user.id, title
        )

    # Проверка лимита сообщений в этом диалоге
    limit = await get_message_limit(current_user.role, db)
    if limit is not None:
        result = await db.execute(
            select(func.count(Message.id))
            .where(
                Message.conversation_id == conversation.id,
                Message.role == "user",
            )
        )
        messages_in_chat = result.scalar() or 0

        if messages_in_chat >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"Лимит сообщений в этом диалоге исчерпан ({limit}). Очистите историю или смените персонажа."
            )

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
        try:
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
        except Exception as e:
            logger.error("Ошибка OpenAI для user_id=%s: %s", current_user.id, str(e))
            yield "Произошла ошибка при генерации ответа."
            return

        # Сохраняем ответ ассистента
        ai_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
        )
        db.add(ai_msg)
        await db.commit()

        logger.info(
            "Ответ сохранён в диалоге %s (длина: %s)",
            conversation.id,
            len(full_response),
        )

    return StreamingResponse(generate(), media_type="text/plain")