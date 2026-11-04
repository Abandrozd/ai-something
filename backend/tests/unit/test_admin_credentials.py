from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def _example_value(name: str) -> str:
    path = Path(__file__).resolve().parents[2] / ".env.example"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            if value == "":
                raise AssertionError(f"{name} in .env.example is empty")
            return value
    raise AssertionError(f"{name} is missing from .env.example")


def _settings(**overrides):
    values = {
        "_env_file": None,
        "API_KEY": "test-key",
        "DATABASE_URL": "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat",
        "SECRET_KEY": "x",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "y",
    }
    values.update(overrides)
    return Settings(**values)


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


def test_startup_rejects_published_example_secrets_only():
    example_secret = _example_value("SECRET_KEY")
    example_password = _example_value("ADMIN_PASSWORD")

    with pytest.raises(ValidationError, match="SECRET_KEY published"):
        _settings(SECRET_KEY=example_secret)

    with pytest.raises(ValidationError, match="ADMIN_PASSWORD published"):
        _settings(ADMIN_PASSWORD=example_password)

    settings = _settings()
    assert settings.SECRET_KEY == "x"
    assert settings.ADMIN_PASSWORD == "y"
    assert settings.ADMIN_USERNAME == "admin"
    assert settings.SECRET_KEY != example_secret
    assert settings.ADMIN_PASSWORD != example_password
