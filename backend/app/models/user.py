from sqlalchemy import (Column,Boolean,Numeric, Integer, String,
                        DateTime, Enum)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    GUEST = "guest"
    WANDERER = "wanderer"
    EXPERT = "expert"
    LEGEND = "legend"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.GUEST,
        nullable=False,
        )
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    balance = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user")