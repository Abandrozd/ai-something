from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.security import get_current_user
from app.services.user_service import create_user, change_password

router = APIRouter(prefix="/users", tags=["users"])


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user_data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
async def change_user_password(
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await change_password(db, current_user, data.old_password, data.new_password)
    return {"message": "Пароль успешно изменён"}