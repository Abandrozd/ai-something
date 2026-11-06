from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.security import get_current_user
from app.models.user import User
from app.dependencies import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.character import Character
from app.schemas.conversation import ConversationResponse, ConversationUpdate
from app.services.character_prompt import opening_greeting
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])



@router.get("/", response_model=list[ConversationResponse])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.is_pinned.desc(), Conversation.id.desc())
    )
    return result.scalars().all()


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        logger.warning(
            "Попытка изменить чужой диалог: user_id=%s, conversation_id=%s",
            current_user.id, conversation_id
            )
        raise HTTPException(status_code=404, detail="Диалог не найден")

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Нечего обновлять")
    if "title" in changes:
        title = changes["title"]
        if not title:
            raise HTTPException(status_code=422, detail="Название не может быть пустым")
        conversation.title = title
    if "is_pinned" in changes:
        if changes["is_pinned"] is None:
            raise HTTPException(status_code=422, detail="Некорректное значение закрепления")
        conversation.is_pinned = changes["is_pinned"]

    await db.commit()
    await db.refresh(conversation)
    logger.info(
        "Пользователь %s обновил диалог %s", current_user.username,
        conversation_id
        )
    return conversation


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Проверяем, что диалог принадлежит пользователю
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        logger.warning(
            "Попытка доступа к чужому диалогу: user_id=%s, conversation_id=%s",
            current_user.id, conversation_id
            )
        raise HTTPException(status_code=404, detail="Диалог не найден")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    logger.info(
        "Пользователь %s удалил диалог %s", current_user.username,
        conversation_id
        )
    await db.delete(conversation)
    await db.commit()
    return {"ok": True}

@router.delete("/{conversation_id}/messages")
async def clear_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    await db.execute(
        Message.__table__.delete().where(Message.conversation_id == conversation_id)
    )
    character = None
    if conversation.character_id:
        character = await db.get(Character, conversation.character_id)
    greeting = opening_greeting(character)
    if greeting:
        db.add(Message(
            conversation_id=conversation.id,
            role="assistant",
            content=greeting,
        ))
    await db.commit()

    logger.info("Пользователь %s очистил историю диалога %s", current_user.username, conversation_id)
    return {"ok": True}