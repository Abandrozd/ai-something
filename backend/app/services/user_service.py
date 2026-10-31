from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.user import User
from app.schemas.user import UserCreate
from app.security import hash_password
from app.logger import get_logger

logger = get_logger(__name__)


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
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


async def change_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
) -> None:
    from app.security import verify_password

    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не короче 6 символов")

    user.hashed_password = hash_password(new_password)
    await db.commit()
    logger.info("Пользователь %s сменил пароль", user.username)