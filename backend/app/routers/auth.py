from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from jose import jwt, JWTError

from app.dependencies import get_db
from app.models.user import User
from app.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Логин. Возвращает access + refresh токены."""
    result = await db.execute(
        select(User).where(User.username == form_data.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Обновляет токены по refresh-токену."""
    try:
        payload = jwt.decode(
            data.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Неверный тип токена")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")

    except JWTError:
        raise HTTPException(status_code=401, detail="Недействительный refresh-токен")

    result = await db.execute(
        select(User).where(User.id == int(user_id), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    new_access = create_access_token({"sub": str(user.id), "role": user.role.value})
    new_refresh = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Выход из системы.
    На текущем этапе просто подтверждает выход.
    Позже можно добавить blacklist refresh-токенов.
    """
    return {"message": "Вы успешно вышли из системы"}