from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class ConversationResponse(BaseModel):
    id: int = Field(..., description="Уникальный идентификатор диалога")
    title: str = Field(..., description="Название диалога")
    character_id: Optional[int] = Field(None, description="ID персонажа, с которым ведётся диалог")
    is_pinned: bool = Field(False, description="Диалог закреплён вверху списка")
    created_at: Optional[datetime] = Field(
        None, description="Дата и время создания диалога"
        )
    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Новое название диалога")
    is_pinned: Optional[bool] = Field(None, description="Закрепить диалог вверху списка")

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Название не может быть пустым")
        return cleaned