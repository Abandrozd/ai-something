from pydantic import BaseModel, Field
from app.models.user import UserRole

class RoleUpdate(BaseModel):
    username: str
    role: UserRole

class BalanceUpdate(BaseModel):
    username: str
    amount: float

class UserStatusUpdate(BaseModel):
    username: str
    is_active: bool

class LimitsUpdate(BaseModel):
    guest: int
    wanderer: int
    expert: int
    legend: int
    admin: int

class LimitsUpdate(BaseModel):
    guest: int = Field(ge=0)
    wanderer: int = Field(ge=0)
    expert: int = Field(ge=0)
    legend: int = Field(ge=0)
    admin: int = Field(ge=0)