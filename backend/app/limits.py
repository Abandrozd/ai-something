from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.settings import AppSetting
from app.models.user import UserRole

DEFAULT_LIMITS = {
    "guest": "5",
    "wanderer": "10",
    "expert": "15",
    "legend": "20",
    "admin": "1000000",  # 0 = без лимита
}

async def get_message_limit(role: UserRole, db: AsyncSession) -> int | None:
    key = f"limit_{role.value}"
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()

    value = int(setting.value) if setting else int(DEFAULT_LIMITS.get(role.value, "5"))
    return None if value >= 100000 else value