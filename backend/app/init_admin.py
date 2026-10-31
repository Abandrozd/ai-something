from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.security import hash_password
from app.config import get_settings
from app.logger import get_logger
logger = get_logger(__name__)

async def create_admin_if_not_exists():

    settings = get_settings()


    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )
        if result.scalar_one_or_none():
            return

        admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
            balance=0,
        )
        session.add(admin)

        await session.commit()
        logger.info("Создан администратор: %s", settings.ADMIN_USERNAME)