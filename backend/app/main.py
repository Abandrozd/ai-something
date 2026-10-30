from contextlib import asynccontextmanager
from app.models import User, Character, Conversation, Message  # noqa: F401
from app.logger import setup_logging, get_logger
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import characters, chat, conversations, user, auth, admin
from app.init_admin import create_admin_if_not_exists
import time

setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_admin_if_not_exists()
    yield


app = FastAPI(
    title="AI Chat API",
    version="0.1.0",
    lifespan=lifespan,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )
app.include_router(characters.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "AI Chat API is running"}


@app.middleware("http")
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
