from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    personality = Column(Text, nullable=True)
    scenario = Column(Text, nullable=True)
    first_message = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)