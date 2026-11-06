from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.dependencies import get_db
from app.models.character import Character
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse
from app.security import get_current_user
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("/", response_model=list[CharacterResponse])
async def get_characters(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    # Shared catalog: any logged-in user can read it. Anonymous clients cannot.
    result = await db.execute(select(Character))
    return result.scalars().all()


@router.post("/", response_model=CharacterResponse)
async def create_character(
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может создавать персонажей")

    character = Character(**data.model_dump())
    db.add(character)
    await db.commit()
    await db.refresh(character)
    logger.info(
        "Админ %s создал персонажа '%s' (id=%s)", current_user.username,
        character.name, character.id
        )
    return character


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    character = await db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return character


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может редактировать персонажей")

    character = await db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)

    await db.commit()
    await db.refresh(character)
    logger.info(
        "Админ %s обновил персонажа id=%s", current_user.username, character_id
        )
    return character


@router.delete("/{character_id}")
async def delete_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может удалять персонажей")

    character = await db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    conversation_ids = (
        await db.execute(
            select(Conversation.id).where(Conversation.character_id == character_id)
        )
    ).scalars().all()
    if conversation_ids:
        await db.execute(
            Message.__table__.delete().where(
                Message.conversation_id.in_(conversation_ids)
            )
        )
        await db.execute(
            Conversation.__table__.delete().where(
                Conversation.id.in_(conversation_ids)
            )
        )

    await db.delete(character)
    await db.commit()
    logger.info(
        "Админ %s удалил персонажа id=%s (%s)", current_user.username,
        character_id, character.name
        )
    return {"ok": True}