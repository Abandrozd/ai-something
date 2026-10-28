from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependecies import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversation import ConversationResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=list[ConversationResponse])
async def get_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation).order_by(Conversation.id.desc())
    )
    return result.scalars().all()


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)):
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    await db.delete(conversation)
    await db.commit()
    return {"ok": True}