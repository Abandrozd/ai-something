from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ConversationResponse(BaseModel):
    id: int = Field(..., description="Уникальный идентификатор диалога")
    title: str = Field(..., description="Название диалога")
    character_id: Optional[int] = Field(None, description="ID персонажа, с которым ведётся диалог")
    created_at: Optional[datetime] = Field(
        None, description="Дата и время создания диалога"
        )
    model_config = {"from_attributes": True}