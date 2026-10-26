import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# echo=False убирает лишний шум в консоли. Поставь True, если хочешь видеть SQL-запросы.
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    """Создает все таблицы в базе, если их еще нет."""
    Base.metadata.create_all(engine)