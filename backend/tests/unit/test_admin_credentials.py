import pytest
from pydantic import ValidationError

from app.config import Settings


def test_admin_password_is_required(monkeypatch):
    for key in (
        "API_KEY",
        "DATABASE_URL",
        "SECRET_KEY",
        "ADMIN_PASSWORD",
        "ADMIN_USERNAME",
        "ADMIN_EMAIL",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            API_KEY="test-key",
            DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat",
            SECRET_KEY="test-secret",
        )


def test_admin_admin_pair_is_rejected():
    with pytest.raises(ValidationError, match="admin/admin"):
        Settings(
            _env_file=None,
            API_KEY="test-key",
            DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat",
            SECRET_KEY="test-secret",
            ADMIN_USERNAME="admin",
            ADMIN_PASSWORD="admin",
        )


def test_custom_admin_password_is_accepted():
    settings = Settings(
        _env_file=None,
        API_KEY="test-key",
        DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat",
        SECRET_KEY="test-secret",
        ADMIN_USERNAME="admin",
        ADMIN_PASSWORD="not-the-default",
    )
    assert settings.ADMIN_PASSWORD == "not-the-default"
    assert settings.ADMIN_USERNAME == "admin"
