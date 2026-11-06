from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()

DATABASE_URL = settings.DATABASE_URL.replace("postgresql+psycopg2", "postgresql+asyncpg")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Schema changes ship as Alembic revisions under app/migrations.
Base = declarative_base()

