from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db

app = FastAPI(title="AI Chat API", version="0.1.0")

# Разрешаем запросы с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def root():
    return {"message": "AI Chat API is running"}