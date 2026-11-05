from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


def _example_value(name: str, path: Path | None = None) -> str:
    if path is None:
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


def test_compose_example_reuses_refused_secret_placeholders():
    backend_example = Path(__file__).resolve().parents[2] / ".env.example"
    root_example = Path(__file__).resolve().parents[3] / ".env.example"
    secret = _example_value("SECRET_KEY", backend_example)
    password = _example_value("ADMIN_PASSWORD", backend_example)

    assert _example_value("SECRET_KEY", root_example) == secret
    assert _example_value("ADMIN_PASSWORD", root_example) == password

    database_url = _example_value("DATABASE_URL", root_example)
    db_user = _example_value("POSTGRES_USER", root_example)
    db_password = _example_value("POSTGRES_PASSWORD", root_example)
    db_name = _example_value("POSTGRES_DB", root_example)
    assert "@postgres:5432/" in database_url
    assert db_user in database_url
    assert db_password in database_url
    assert database_url.endswith(f"/{db_name}")
    assert db_password not in {secret, password}
    assert _example_value("FRONTEND_ORIGIN", root_example) == "http://localhost:5173"


def test_app_does_not_create_schema_with_create_all():
    database = Path(__file__).resolve().parents[2] / "app" / "database.py"
    source = database.read_text(encoding="utf-8")
    assert "create_all" not in source
    assert "init_db" not in source
