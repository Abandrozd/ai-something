from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from app.logger import get_logger
from app.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.dependencies import get_db
from app.models.user import User
from app.request_limits import (
    enforce_login_limit,
    enforce_refresh_limit,
    reject_long_password,
)
from app.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_payload,
)
logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


def _presented_refresh_token(request: Request, data: RefreshRequest | None) -> str:
    """Body token wins when a client sends one. Browsers send the cookie."""
    if data is not None and data.refresh_token:
        return data.refresh_token
    cookie = request.cookies.get(REFRESH_COOKIE)
    if cookie:
        return cookie
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный refresh-токен",
    )


def _store_session(response: Response, request: Request, user: User) -> dict:
    issued = _issue_tokens(user)
    set_auth_cookies(
        response, request, issued["access_token"], issued["refresh_token"],
    )
    return {"token_type": "bearer"}


def _issue_tokens(user: User) -> dict:
    version = int(user.token_version or 0)
    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "ver": version}
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id), "ver": version}
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def _user_from_refresh(token: str, db: AsyncSession) -> User:
    payload = decode_refresh_payload(token)
    result = await db.execute(
        select(User).where(User.id == int(payload["sub"]), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if payload.get("ver") != int(user.token_version or 0):
        raise HTTPException(status_code=401, detail="Недействительный refresh-токен")
    return user


async def _rotate_session(user: User, db: AsyncSession) -> None:
    """Bump the session version once, so this refresh cannot be replayed.

    A second presentation of the same refresh loses the compare-and-swap and
    does not mint another pair. Access tokens carry the same version, so the
    pair that was just replaced stops matching too.
    """
    expected = int(user.token_version or 0)
    result = await db.execute(
        update(User)
        .where(User.id == user.id, User.token_version == expected)
        .values(token_version=expected + 1)
        .returning(User.token_version)
    )
    new_version = result.scalar_one_or_none()
    if new_version is None:
        await db.rollback()
        raise HTTPException(status_code=401, detail="Недействительный refresh-токен")
    db.expire(user)
    await db.commit()
    await db.refresh(user)


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Логин. Кладёт access и refresh в httpOnly cookie, без тела с токенами."""
    enforce_login_limit(request, form_data.username)
    reject_long_password(form_data.password)
    logger.info("Попытка входа: %s", form_data.username)
    result = await db.execute(
        select(User).where(User.username == form_data.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Пользователь не найден: %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Успешный вход: %s", user.username)
    return _store_session(response, request, user)


@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    data: RefreshRequest | None = None,
):
    """Обновляет пару и отзывает предыдущий refresh."""
    enforce_refresh_limit(request)
    try:
        user = await _user_from_refresh(_presented_refresh_token(request, data), db)
        await _rotate_session(user, db)
    except HTTPException:
        logger.warning("Неудачная попытка обновления токена")
        raise

    logger.info("Обновление токена для user_id=%s", user.id)
    return _store_session(response, request, user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    data: RefreshRequest | None = None,
):
    """Отзывает сессию: ранее выданные access и refresh перестают подходить."""
    user = await _user_from_refresh(_presented_refresh_token(request, data), db)
    user.token_version = int(user.token_version or 0) + 1
    await db.commit()
    clear_auth_cookies(response, request)
    logger.info(
        "Выход из системы: %s (id=%s)", user.username, user.id
    )
    return {"message": "Вы успешно вышли из системы"}