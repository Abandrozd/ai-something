from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

# Exact placeholder strings committed in backend/.env.example.
# A copied example must not boot. Other values, including short ones, are left alone.
_EXAMPLE_SECRET_KEY = "replace-with-a-long-random-string"
_EXAMPLE_ADMIN_PASSWORD = "replace-with-a-strong-password"


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
    # Single browser origin allowed to call the API with credentials.
    # Cookie sessions must not be paired with a reflected wildcard origin.
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def reject_published_example_secrets(self):
        if self.SECRET_KEY == _EXAMPLE_SECRET_KEY:
            raise ValueError(
                "Refusing to start with the SECRET_KEY published in .env.example. "
                "Set SECRET_KEY to your own value."
            )
        if self.ADMIN_PASSWORD == _EXAMPLE_ADMIN_PASSWORD:
            raise ValueError(
                "Refusing to start with the ADMIN_PASSWORD published in .env.example. "
                "Set ADMIN_PASSWORD to your own value."
            )
        return self

    @model_validator(mode="after")
    def reject_known_admin_credentials(self):
        if self.ADMIN_USERNAME == "admin" and self.ADMIN_PASSWORD == "admin":
            raise ValueError(
                "Refusing to start with the admin/admin credentials. "
                "Set ADMIN_PASSWORD to a value other than admin."
            )
        return self

    @model_validator(mode="after")
    def reject_wildcard_frontend_origin(self):
        origin = (self.FRONTEND_ORIGIN or "").strip()
        if not origin or origin == "*":
            raise ValueError(
                "FRONTEND_ORIGIN must be one concrete origin. "
                "A wildcard plus credentials would expose cookie sessions."
            )
        self.FRONTEND_ORIGIN = origin
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()