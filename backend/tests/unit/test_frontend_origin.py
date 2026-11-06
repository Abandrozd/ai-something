import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**extra):
    return Settings(
        _env_file=None,
        API_KEY="test-key",
        DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat",
        SECRET_KEY="test-secret",
        ADMIN_PASSWORD="not-the-default",
        **extra,
    )


def test_frontend_origin_defaults_to_vite_dev_server():
    settings = _settings()
    assert settings.FRONTEND_ORIGIN == "http://localhost:5173"


def test_frontend_origin_is_overridable():
    settings = _settings(FRONTEND_ORIGIN="http://localhost:4173")
    assert settings.FRONTEND_ORIGIN == "http://localhost:4173"


@pytest.mark.parametrize("origin", ["*", "", "   "])
def test_wildcard_frontend_origin_is_rejected(origin):
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN"):
        _settings(FRONTEND_ORIGIN=origin)
