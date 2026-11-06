from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.main import create_app

DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


def _example_text() -> str:
    path = Path(__file__).resolve().parents[2] / ".env.example"
    return path.read_text(encoding="utf-8")


def test_api_docs_flag_defaults_off_and_is_documented():
    example = _example_text()
    assert "ENABLE_API_DOCS" in example
    assert "/docs" in example
    assert "/redoc" in example
    assert "/openapi.json" in example

    settings = Settings(
        _env_file=None,
        API_KEY="test-key",
        DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat",
        SECRET_KEY="test-secret",
        ADMIN_PASSWORD="not-the-default",
    )
    assert settings.ENABLE_API_DOCS is False


@pytest.mark.asyncio
async def test_api_docs_are_hidden_without_flag(client):
    for path in DOC_PATHS:
        response = await client.get(path)
        assert response.status_code == 404, path
        assert "paths" not in response.text
        assert "swagger" not in response.text.lower()


@pytest.mark.asyncio
async def test_api_docs_are_served_when_flag_is_set(monkeypatch):
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    get_settings.cache_clear()
    try:
        enabled = create_app()
        transport = ASGITransport(app=enabled)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            docs = await ac.get("/docs")
            redoc = await ac.get("/redoc")
            schema = await ac.get("/openapi.json")
    finally:
        get_settings.cache_clear()

    assert docs.status_code == 200
    assert "swagger" in docs.text.lower()
    assert redoc.status_code == 200
    assert "redoc" in redoc.text.lower()
    assert schema.status_code == 200
    payload = schema.json()
    assert "/characters/" in payload["paths"]
    assert "/chat/" in payload["paths"]
