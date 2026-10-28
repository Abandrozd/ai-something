import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

from backend.app.database import init_db, SessionLocal
from models import User, Conversation, Message, Character 

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini")

app = FastAPI(title="AI Chat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], # Разрешаем все методы, включая DELETE
    allow_headers=["*"],
)

init_db()

# --- СХЕМЫ ДАННЫХ (Pydantic) ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: int | None = None
    character_id: int | None = None # <-- Добавили! Чтобы при создании нового чата знать, с кем говорим

class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    username: str

# Схемы для создания и отображения персонажей
class CharacterCreate(BaseModel):
    name: str
    description: str | None = None
    personality: str | None = None
    scenario: str | None = None
    first_message: str | None = None

class CharacterUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    personality: str | None = None
    scenario: str | None = None
    first_message: str | None = None

class CharacterResponse(BaseModel):
    id: int
    name: str
    description: str | None
    personality: str | None
    scenario: str | None
    first_message: str | None

    class Config:
        from_attributes = True # Позволяет FastAPI читать данные прямо из SQLAlchemy моделей

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ЭНДПОИНТЫ ДЛЯ ПЕРСОНАЖЕЙ ---

@app.post("/characters", response_model=CharacterResponse)
def create_character(char: CharacterCreate, db: Session = Depends(get_db)):
    """Создает нового персонажа в базе"""
    new_char = Character(**char.model_dump())
    db.add(new_char)
    db.commit()
    db.refresh(new_char)
    return new_char

@app.get("/characters", response_model=list[CharacterResponse])
def get_characters(db: Session = Depends(get_db)):
    """Возвращает список всех персонажей"""
    return db.query(Character).all()

# --- ОСНОВНОЙ ЭНДПОИНТ ЧАТА ---

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Ищем или создаем пользователя
    user = db.query(User).filter_by(username="web_user").first()
    if not user:
        user = User(username="web_user")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Ищем или создаем чат
    if request.conversation_id:
        conversation = db.query(Conversation).filter_by(id=request.conversation_id, user_id=user.id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Чат не найден")
    else:
        conversation = Conversation(
            user_id=user.id, 
            title="Web chat",
            character_id=request.character_id
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        # Если это новый чат, добавляем первое сообщение персонажа
        if request.character_id:
            char = db.query(Character).filter_by(id=request.character_id).first()
            if char and char.first_message:
                init_msg = Message(conversation_id=conversation.id, role="assistant", content=char.first_message)
                db.add(init_msg)
                db.commit()

    # 3. Достаем персонажа для формирования промпта
    character = db.query(Character).filter_by(id=conversation.character_id).first()

    if character:
        system_prompt = f"""Ты — {character.name}. 
Твоя личность: {character.personality}.
Твое описание: {character.description}.
Контекст сцены: {character.scenario}.
Отвечай строго от лица этого персонажа, не выходи из роли. Не упоминай, что ты ИИ."""
    else:
        system_prompt = "Ты — дружелюбный ассистент."

    # 4. Сохраняем сообщение юзера
    user_msg = Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_msg)
    db.flush() 
    
    # 5. Формируем историю
    db_messages = db.query(Message).filter_by(conversation_id=conversation.id).order_by(Message.id).all()
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in db_messages:
        api_messages.append({"role": m.role, "content": m.content})

    # 6. Генератор для стриминга
    async def stream_generator():
        full_response = ""
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                stream=True,
                temperature=0.7
            )
            
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    yield content 
            
            # Когда поток закончился, сохраняем полный ответ в БД
            ai_msg = Message(conversation_id=conversation.id, role="assistant", content=full_response)
            db.add(ai_msg)
            db.commit()
            
        except Exception as e:
            db.rollback()
            yield f"\n[Ошибка ИИ: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")

# --- ЭНДПОИНТЫ ДЛЯ ИСТОРИИ ---

@app.get("/conversations")
def get_conversations(db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username="web_user").first()
    if not user:
        return []
    
    convs = db.query(Conversation).filter_by(user_id=user.id).order_by(Conversation.id.desc()).all()
    
    # Добавили имя персонажа в ответ, чтобы фронтенд мог красиво отрисовать список
    result = []
    for c in convs:
        char = db.query(Character).filter_by(id=c.character_id).first()
        result.append({
            "id": c.id, 
            "title": char.name if char else "Обычный чат", 
            "created_at": c.created_at
        })
    return result

@app.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.id).all()
    return [{"role": m.role, "content": m.content} for m in msgs]

@app.get("/characters/{character_id}", response_model=CharacterResponse)
def get_character(character_id: int, db: Session = Depends(get_db)):
    char = db.query(Character).filter_by(id=character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    return char

# --- ЭНДОПОИНТЫ ДЛЯ ИЗМЕНЕНИЯ ---

@app.patch("/characters/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: int,
    char_data: CharacterUpdate,
    db: Session = Depends(get_db),
):
    """Частично обновляет карточку персонажа. Меняются только присланные поля."""
    char = db.query(Character).filter_by(id=character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Персонаж не найден")

    # exclude_unset=True -> в dict попадут ТОЛЬКО поля, которые клиент реально прислал
    updates = char_data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(char, field, value)

    db.commit()
    db.refresh(char)
    return char

# --- ЭНДПОИНТЫ ДЛЯ УДАЛЕНИЯ ---

@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Удаляет чат и все его сообщения (благодаря cascade в models.py)"""
    conv = db.query(Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Чат не найден")
    
    db.delete(conv)
    db.commit()
    return {"message": "Чат успешно удален"}

@app.delete("/characters/{character_id}")
def delete_character(character_id: int, db: Session = Depends(get_db)):
    """Удаляет персонажа и все его чаты."""
    char = db.query(Character).filter_by(id=character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Персонаж не найден")
    
    # 1. Ищем все чаты этого персонажа
    convs = db.query(Conversation).filter_by(character_id=character_id).all()
    
    # 2. Удаляем их по одному через ORM (это вызовет каскадное удаление сообщений)
    for conv in convs:
        db.delete(conv)
    
    # 3. Теперь удаляем самого персонажа
    db.delete(char)
    db.commit()
    
    return {"message": "Персонаж и его чаты удалены"}
