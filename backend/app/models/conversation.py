from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    title = Column(String, nullable=False, default="New chat")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="conversations")
    character = relationship("Character")
    messages = relationship("Message",
                            back_populates="conversation",
                            order_by="Message.id",
                            cascade="all, delete-orphan")
