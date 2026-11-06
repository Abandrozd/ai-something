import os
import sys
from pathlib import Path

import pytest

# Сначала добавляем путь
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Импорт приложения читает настройки сразу. Подставляем заглушки, чтобы
# тесты собирались без .env и без настоящего ключа OpenAI.
os.environ.setdefault("API_KEY", "test-not-a-real-openai-key")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chat")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin-password")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base
from app.dependencies import get_db
from app.request_limits import limiter

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class _Delta:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.delta = _Delta(content)


class _Chunk:
    def __init__(self, content):
        self.choices = [_Choice(content)]


@pytest.fixture(autouse=True)
def reset_request_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(autouse=True)
def mock_model(monkeypatch):
    """Подменяет вызов модели, чтобы тесты чата не ходили в OpenAI."""
    state = {
        "chunks": ["mocked reply"],
        "error": None,
        "factory": None,
        "calls": [],
    }

    async def create_chat_completion(*, model, messages, stream):
        state["calls"].append({
            "model": model,
            "messages": messages,
            "stream": stream,
        })
        if state["error"] is not None:
            raise state["error"]
        if state["factory"] is not None:
            return state["factory"]()

        chunks = list(state["chunks"])

        async def stream_chunks():
            for text in chunks:
                yield _Chunk(text)

        return stream_chunks()

    monkeypatch.setattr(
        "app.routers.chat.create_chat_completion",
        create_chat_completion,
    )
    return state