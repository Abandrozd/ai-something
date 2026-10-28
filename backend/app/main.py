from contextlib import asynccontextmanager
from app.models import User, Character, Conversation, Message  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import characters, chat, conversations

app = FastAPI(
    title="AI Chat API",
    version="0.1.0",
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
@app.get("/")
async def root():
    return {"message": "AI Chat API is running"}