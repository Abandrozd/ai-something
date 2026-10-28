from pydantic import BaseModel, Field
from typing import Optional


class CharacterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Имя персонажа")
    description: Optional[str] = Field(None, description="Краткое описание персонажа")
    personality: Optional[str] = Field(None, description="Характер и особенности поведения")
    scenario: Optional[str] = Field(None, description="Сценарий / контекст общения")
    first_message: Optional[str] = Field(None, description="Первое сообщение персонажа")
    avatar_url: Optional[str] = Field(None, description="Ссылка на аватар")


class CharacterCreate(CharacterBase):
    pass


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Имя персонажа")
    description: Optional[str] = Field(None, description="Краткое описание персонажа")
    personality: Optional[str] = Field(None, description="Характер и особенности поведения")
    scenario: Optional[str] = Field(None, description="Сценарий / контекст общения")
    first_message: Optional[str] = Field(None, description="Первое сообщение персонажа")
    avatar_url: Optional[str] = Field(None, description="Ссылка на аватар")


class CharacterResponse(CharacterBase):
    id: int = Field(..., description="Уникальный идентификатор персонажа")

    model_config = {"from_attributes": True}