from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.security import hash_password, get_current_user
from app.logger import get_logger
from pydantic import BaseModel
logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    if result.scalar_one_or_none():
        logger.warning("Попытка регистрации существующего: %s", user_data.username)
        raise HTTPException(status_code=409, detail="Пользователь уже существует")

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    logger.info("Зарегистрирован: %s", db_user.username)
    return db_user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.security import verify_password, hash_password

    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Новый пароль должен быть не короче 6 символов")

    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()

    logger.info("Пользователь %s сменил пароль", current_user.username)
    return {"message": "Пароль успешно изменён"}