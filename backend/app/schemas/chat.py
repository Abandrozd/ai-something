from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Текст сообщения пользователя")
    conversation_id: Optional[int] = Field(None, description="ID существующего диалога (если продолжаем)")
    character_id: Optional[int] = Field(None, description="ID персонажа (если начинаем новый диалог)")