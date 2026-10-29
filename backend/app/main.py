from contextlib import asynccontextmanager
from app.models import User, Character, Conversation, Message  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import characters, chat, conversations, user, auth
from app.init_admin import create_admin_if_not_exists

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
@app.get("/")
async def root():
    return {"message": "AI Chat API is running"}



