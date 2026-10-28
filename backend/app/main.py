import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

from database import init_db, SessionLocal
from models import User, Conversation, Message

# Фикс кодировки для консоли Windows
sys.stdin.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

client = OpenAI(api_key=os.getenv("API_KEY"))
MODEL = os.getenv("MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = "Ты — дружелюбный ассистент. Отвечай кратко на русском."

def main():
    init_db()
    session = SessionLocal()

    user = session.query(User).filter_by(username="local_user").first()
    if not user:
        user = User(username="local_user")
        session.add(user)
        session.commit()
        session.refresh(user)

    conversation = (
        session.query(Conversation)
        .filter_by(user_id=user.id)
        .order_by(Conversation.id.desc())
        .first()
    )
    if not conversation:
        conversation = Conversation(user_id=user.id, title="Консольный чат")
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

    print("Чат запущен. Введите 'exit' для выхода.\n")

    while True:
        user_text = input("Вы: ").strip()
        if user_text.lower() in ("exit", "quit"):
            break
        if not user_text:
            continue

        user_msg = Message(conversation_id=conversation.id, role="user", content=user_text)
        session.add(user_msg)
        session.flush()
        
        # Фикс предупреждения SQLAlchemy
        session.expire_all()

        db_messages = (
            session.query(Message)
            .filter_by(conversation_id=conversation.id)
            .order_by(Message.id)
            .all()
        )

        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in db_messages:
            api_messages.append({"role": m.role, "content": m.content})

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages
            )
            answer = response.choices[0].message.content
        except Exception as e:
            print(f"\n[Ошибка API] {e}\n")
            session.rollback()
            continue

        print(f"ИИ: {answer}\n")

        ai_msg = Message(conversation_id=conversation.id, role="assistant", content=answer)
        session.add(ai_msg)
        session.commit()

    session.close()
    print("Сессия закрыта. Пока!")

if __name__ == "__main__":
    main()