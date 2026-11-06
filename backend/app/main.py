from contextlib import asynccontextmanager
from app.models import User, Character, Conversation, Message  # noqa: F401
from app.logger import setup_logging, get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import characters, chat, conversations, user, auth, admin
from app.init_admin import create_admin_if_not_exists
from app.config import get_settings
import time

setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_admin_if_not_exists()
    yield


def create_app() -> FastAPI:
    """Build the API. Docs routes exist only when ENABLE_API_DOCS is set."""
    docs_enabled = get_settings().ENABLE_API_DOCS
    application = FastAPI(
        title="AI Chat API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().FRONTEND_ORIGIN],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Conversation-Id"],
    )
    application.include_router(characters.router)
    application.include_router(chat.router)
    application.include_router(conversations.router)
    application.include_router(user.router)
    application.include_router(auth.router)
    application.include_router(admin.router)

    @application.get("/")
    async def root():
        return {"message": "AI Chat API is running"}

    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration = round(time.time() - start, 3)

        # Логируем только ошибки и медленные запросы
        if response.status_code >= 400 or duration > 1.0:
            logger.warning(
                "%s %s → %s (%ss)",
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )
        return response

    return application


app = create_app()
