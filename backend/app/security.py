from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserRole
from app.config import get_settings
from app.cookies import ACCESS_COOKIE
from app.dependencies import get_db
from app.models.user import User

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
settings = get_settings()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    to_encode.update({
        "exp": expire,
        "type": "access",
        "ver": int(data.get("ver", 0) or 0),
        })
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM,
        )


async def get_current_user(
        request: Request,
        header_token: str | None = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        ):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
        )
    # An explicit Authorization header is the token under test. The httpOnly
    # cookie is the browser session and is used only when no header is sent.
    token = header_token or request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            )
        user_id: str = payload.get("sub")
        # Refresh tokens are signed with the same key, but they are not a session.
        if user_id is None or payload.get("type") != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == int(user_id), User.is_active == True),
        )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    # token_version moves on logout, password change, and refresh rotation.
    # An access token from before that must not keep working until its exp.
    if payload.get("ver") != int(user.token_version or 0):
        raise credentials_exception
    return user


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "ver": int(data.get("ver", 0) or 0),
        })
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM,
        )


def decode_refresh_payload(token: str) -> dict:
    """Validate a refresh token and return its payload.

    Access tokens and garbage are rejected. Revocation is checked by the
    caller against the user's token_version.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh-токен",
            )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
            )
    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
            )
    return payload


async def get_current_admin(
        current_user: User = Depends(get_current_user),
        ) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только для администраторов",
            )
    return current_user
