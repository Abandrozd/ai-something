from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.security import hash_password, get_current_user
from pydantic import BaseModel
from app.models.user import UserRole
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

    user.is_active = data.is_active
    await db.commit()
    return {"username": user.username, "is_active": user.is_active}