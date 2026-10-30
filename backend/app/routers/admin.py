from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.dependencies import get_db
from app.models.user import User, UserRole
from app.models.conversation import Conversation
from app.models.settings import AppSetting
from app.schemas.user import UserResponse
from app.security import get_current_user, get_current_admin
from app.limits import DEFAULT_LIMITS
from app.logger import get_logger
from app.schemas.admin import RoleUpdate, BalanceUpdate, UserStatusUpdate, LimitsUpdate
logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")
    return current_user


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.patch("/users/role")
async def update_user_role(
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.role = data.role
    await db.commit()
    await db.refresh(user)

    logger.info("Админ %s сменил роль %s → %s", admin.username, user.username, data.role)
    return {"username": user.username, "role": user.role.value}


@router.patch("/users/balance")
async def update_balance(
    data: BalanceUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.balance = float(user.balance or 0) + data.amount
    await db.commit()
    await db.refresh(user)

    logger.info("Админ %s изменил баланс %s на %s", admin.username, user.username, data.amount)
    return {"username": user.username, "balance": user.balance}


@router.patch("/users/status")
async def update_user_status(
    data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = data.is_active
    await db.commit()

    action = "заблокировал" if not data.is_active else "разблокировал"
    logger.info("Админ %s %s пользователя %s", admin.username, action, user.username)
    return {"username": user.username, "is_active": user.is_active}


@router.get("/limits")
async def get_limits(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    limits = {}
    for role in ["guest", "wanderer", "expert", "legend", "admin"]:
        key = f"limit_{role}"
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        limits[role] = int(setting.value) if setting else int(DEFAULT_LIMITS[role])
    return limits


@router.put("/limits")
async def update_limits(
    data: LimitsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    for role, value in data.items():
        if role not in DEFAULT_LIMITS:
            continue
        key = f"limit_{role}"
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value)))
    await db.commit()
    logger.info("Админ %s обновил лимиты: %s", admin.username, data)
    return {"ok": True}


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
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