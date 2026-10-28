from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    GUEST = "guest"
    WANDERER = "wanderer"
    EXPERT = "expert"
    LEGEND = "legend"
    ADMIN = "admin"

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.GUEST

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    balance: float

    model_config = {"from_attributes": True}