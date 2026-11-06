from pydantic import BaseModel, ConfigDict, EmailStr, Field
from enum import Enum
from typing import Optional

from app.request_limits import MAX_PASSWORD_LENGTH

class UserRole(str, Enum):
    GUEST = "guest"
    WANDERER = "wanderer"
    EXPERT = "expert"
    LEGEND = "legend"
    ADMIN = "admin"

class UserCreate(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=MAX_PASSWORD_LENGTH)

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    balance: float

    model_config = {"from_attributes": True}