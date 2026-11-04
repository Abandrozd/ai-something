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
from app.services.character_prompt import build_system_prompt, opening_greeting
from openai import AsyncOpenAI

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()
client = AsyncOpenAI(api_key=settings.API_KEY)


async def create_chat_completion(*, model: str, messages: list, stream: bool):
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        stream=stream,
    )


async def collect_model_text(api_messages: list) -> str:
    """Забирает ответ модели целиком, чтобы сбой upstream не стал телом 200."""
    stream = await create_chat_completion(
        model=settings.MODEL,
        messages=api_messages,
        stream=True,
    )
    parts: list[str] = []
    async for chunk in stream:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        text = getattr(delta, "content", None) if delta is not None else None
        if text:
            parts.append(text)
    return "".join(parts)


async def replay(text: str):
    yield text


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

    conversation = None
    character = None
    if data.conversation_id is not None:
        conversation = await db.get(Conversation, data.conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Диалог не найден")
        if conversation.user_id != current_user.id:
            logger.warning(
                "Попытка доступа к чужому диалогу: user_id=%s, conversation_id=%s",
                current_user.id, data.conversation_id
            )
            raise HTTPException(status_code=403, detail="Нет доступа к этому диалогу")
        if conversation.character_id:
            character = await db.get(Character, conversation.character_id)
    else:
        if data.character_id is None:
            raise HTTPException(status_code=400, detail="Не выбран персонаж")
        character = await db.get(Character, data.character_id)
        if character is None:
            raise HTTPException(status_code=404, detail="Персонаж не найден")

    # Проверка лимита сообщений в этом диалоге
    limit = await get_message_limit(current_user.role, db)
    if limit is not None:
        if conversation is None:
            messages_in_chat = 0
        else:
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

    history = []
    if conversation is not None:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id)
        )
        history = result.scalars().all()

    api_messages = []
    greeting = opening_greeting(character)
    if character:
        api_messages.append({
            "role": "system",
            "content": build_system_prompt(character),
        })

    # Приветствия ещё нет в истории: новый диалог или история без реплик.
    # Уже сохранённое приветствие приезжает вместе с history.
    if greeting and not history:
        api_messages.append({"role": "assistant", "content": greeting})

    for m in history:
        api_messages.append({"role": m.role, "content": m.content})
    api_messages.append({"role": "user", "content": data.message})

    try:
        full_response = await collect_model_text(api_messages)
    except Exception as e:
        logger.error("Ошибка OpenAI для user_id=%s: %s", current_user.id, str(e))
        raise HTTPException(
            status_code=502,
            detail="Произошла ошибка при генерации ответа.",
        ) from e

    if conversation is None:
        conversation = Conversation(
            user_id=current_user.id,
            character_id=character.id,
            title=character.name or "New chat",
        )
        db.add(conversation)
        await db.flush()
        logger.info(
            "Создан новый диалог id=%s для user_id=%s (персонаж: %s)",
            conversation.id, current_user.id, conversation.title
        )

    conversation_id = conversation.id
    if greeting and not history:
        db.add(Message(
            conversation_id=conversation_id,
            role="assistant",
            content=greeting,
        ))
    db.add(Message(
        conversation_id=conversation_id,
        role="user",
        content=data.message,
    ))
    db.add(Message(
        conversation_id=conversation_id,
        role="assistant",
        content=full_response,
    ))
    await db.commit()

    logger.info(
        "Ответ сохранён в диалоге %s (длина: %s)",
        conversation_id,
        len(full_response),
    )

    return StreamingResponse(
        replay(full_response),
        media_type="text/plain",
        headers={"X-Conversation-Id": str(conversation_id)},
    )
