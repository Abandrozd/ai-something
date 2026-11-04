from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_KEY: str
    MODEL: str = "gpt-4o-mini"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def reject_known_admin_credentials(self):
        if self.ADMIN_USERNAME == "admin" and self.ADMIN_PASSWORD == "admin":
            raise ValueError(
                "Refusing to start with the admin/admin credentials. "
                "Set ADMIN_PASSWORD to a value other than admin."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()