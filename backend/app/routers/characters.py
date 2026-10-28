from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse

router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("/", response_model=list[CharacterResponse])
async def get_characters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Character))
    return result.scalars().all()


@router.post("/", response_model=CharacterResponse)
async def create_character(
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
):
    character = Character(**data.model_dump())
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: int, db: AsyncSession = Depends(get_db)):
    character = await db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return character


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: int,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
):
    character = await db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(character, key, value)

    await db.commit()
    await db.refresh(character)
    return character


@router.delete("/{character_id}")
async def delete_character(character_id: int, db: AsyncSession = Depends(get_db)):
    character = await db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    await db.delete(character)
    await db.commit()
    return {"ok": True}