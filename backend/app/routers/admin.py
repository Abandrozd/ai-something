from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.admin import RoleUpdate, BalanceUpdate, UserStatusUpdate, LimitsUpdate
from app.security import get_current_admin
from app.services.admin_service import (
    get_all_users,
    update_user_role,
    update_balance,
    update_user_status,
    get_limits,
    update_limits,
    get_stats,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await get_all_users(db)


@router.patch("/users/role")
async def change_role(
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await update_user_role(db, data, admin)
    return {"username": user.username, "role": user.role.value}


@router.patch("/users/balance")
async def change_balance(
    data: BalanceUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await update_balance(db, data, admin)
    return {"username": user.username, "balance": user.balance}


@router.patch("/users/status")
async def change_status(
    data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await update_user_status(db, data, admin)
    return {"username": user.username, "is_active": user.is_active}


@router.get("/limits")
async def read_limits(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await get_limits(db)


@router.put("/limits")
async def write_limits(
    data: LimitsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    await update_limits(db, data, admin)
    return {"ok": True}


@router.get("/stats")
async def read_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await get_stats(db)