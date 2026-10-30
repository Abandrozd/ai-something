from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.settings import AppSetting
from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.security import hash_password, get_current_user
from pydantic import BaseModel
from app.models.user import UserRole
from app.logger import get_logger
from app.limits import get_message_limit, DEFAULT_LIMITS
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from app.models.conversation import Conversation


logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


class RoleUpdate(BaseModel):
    username: str
    role: UserRole

class BalanceUpdate(BaseModel):
    username: str
    amount: float


class UserStatusUpdate(BaseModel):
    username: str
    is_active: bool

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.username == user_data.username)
        )
    )
    if result.scalar_one_or_none():
        logger.warning(
            "Попытка регистрации существующего пользователя: %s / %s",
            user_data.username, user_data.email
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email или username уже существует",
        )

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(
        "Зарегистрирован новый пользователь: %s (id=%s)", db_user.username,
        db_user.id
        )
    return db_user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Возвращает данные текущего пользователя."""
    return current_user

@router.patch("/role")
async def update_user_role(
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только администратор может менять роли")

    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.role = data.role
    await db.commit()
    await db.refresh(user)
    logger.info(
        "Админ %s сменил роль пользователя %s: %s → %s",
        current_user.username, user.username, user.role, data.role
        )
    return {
        "username": user.username,
        "role": user.role.value,
    }

@router.get("/", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "Попытка просмотра пользователей без прав: %s",
            current_user.username
            )
        raise HTTPException(status_code=403, detail="Только для администраторов")

    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()

@router.patch("/balance")
async def update_balance(
    data: BalanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")

    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.balance = float(user.balance or 0) + data.amount
    await db.commit()
    await db.refresh(user)
    logger.info(
        "Админ %s изменил баланс %s на %s (итого: %s)",
        current_user.username, user.username, data.amount, user.balance
        )
    return {"username": user.username, "balance": user.balance}


@router.patch("/status")
async def update_user_status(
    data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")

    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    action = "заблокировал" if not data.is_active else "разблокировал"
    logger.info(
        "Админ %s %s пользователя %s", current_user.username, action,
        user.username
        )
    user.is_active = data.is_active
    await db.commit()
    return {"username": user.username, "is_active": user.is_active}

@router.get("/limits")
async def get_limits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")

    limits = {}
    for role in ["guest", "wanderer", "expert", "legend", "admin"]:
        key = f"limit_{role}"
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        limits[role] = int(setting.value) if setting else int(DEFAULT_LIMITS[role])
    return limits


@router.put("/limits")
async def update_limits(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")

    for role, value in data.items():
        key = f"limit_{role}"
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value)))
    await db.commit()
    return {"ok": True}


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Всего пользователей
    total_users = await db.scalar(select(func.count(User.id)))

    # Новых сегодня
    new_today = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )

    # Новых за неделю
    new_week = await db.scalar(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )

    # Всего диалогов
    total_conversations = await db.scalar(select(func.count(Conversation.id)))

    # Активных пользователей (is_active = True)
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )

    return {
        "total_users": total_users or 0,
        "new_today": new_today or 0,
        "new_week": new_week or 0,
        "total_conversations": total_conversations or 0,
        "active_users": active_users or 0,
    }