from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from app.request_limits import MAX_MESSAGE_LENGTH


class ChatRequest(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="Текст сообщения пользователя",
    )
    conversation_id: Optional[int] = Field(None, description="ID существующего диалога (если продолжаем)")
    character_id: Optional[int] = Field(None, description="ID персонажа (если начинаем новый диалог)")