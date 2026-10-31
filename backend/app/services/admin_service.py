from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.models.user import User, UserRole
from app.models.conversation import Conversation
from app.models.settings import AppSetting
from app.schemas.admin import RoleUpdate, BalanceUpdate, UserStatusUpdate, LimitsUpdate
from app.limits import DEFAULT_LIMITS
from app.logger import get_logger

logger = get_logger(__name__)


async def get_all_users(
    db: AsyncSession,
    search: str | None = None,
    role: str | None = None,
):
    query = select(User)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        )

    if role:
        query = query.where(User.role == role)

    query = query.order_by(User.id)
    result = await db.execute(query)
    return result.scalars().all()


async def update_user_role(db: AsyncSession, data: RoleUpdate, admin: User):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.role = data.role
    await db.commit()
    await db.refresh(user)

    logger.info("Админ %s сменил роль %s → %s", admin.username, user.username, data.role)
    return user


async def update_balance(db: AsyncSession, data: BalanceUpdate, admin: User):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.balance = float(user.balance or 0) + data.amount
    await db.commit()
    await db.refresh(user)

    logger.info("Админ %s изменил баланс %s на %s", admin.username, user.username, data.amount)
    return user


async def update_user_status(db: AsyncSession, data: UserStatusUpdate, admin: User):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = data.is_active
    await db.commit()

    action = "заблокировал" if not data.is_active else "разблокировал"
    logger.info("Админ %s %s пользователя %s", admin.username, action, user.username)
    return user


async def get_limits(db: AsyncSession) -> dict:
    limits = {}
    for role in DEFAULT_LIMITS.keys():
        key = f"limit_{role}"
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        limits[role] = int(setting.value) if setting else int(DEFAULT_LIMITS[role])
    return limits


async def update_limits(db: AsyncSession, data: LimitsUpdate, admin: User):
    limits_dict = data.model_dump()
    for role, value in limits_dict.items():
        key = f"limit_{role}"
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value)))
    await db.commit()
    logger.info("Админ %s обновил лимиты", admin.username)


async def get_stats(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    total_users = await db.scalar(select(func.count(User.id)))
    new_today = await db.scalar(select(func.count(User.id)).where(User.created_at >= today_start))
    new_week = await db.scalar(select(func.count(User.id)).where(User.created_at >= week_start))
    total_conversations = await db.scalar(select(func.count(Conversation.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))

    return {
        "total_users": total_users or 0,
        "new_today": new_today or 0,
        "new_week": new_week or 0,
        "total_conversations": total_conversations or 0,
        "active_users": active_users or 0,
    }