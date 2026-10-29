
```markdown
# AI Chat

Веб-приложение для общения с AI-персонажами.  
Бэкенд на FastAPI + PostgreSQL, фронтенд на React + Vite.

## Требования

- Python 3.10+
- PostgreSQL
- Node.js (LTS)

## Установка и запуск

### 1. База данных

Создайте базу в PostgreSQL:

```sql
CREATE DATABASE ai_chat;
```

### 2. Бэкенд

```bash
cd backend
```

Создайте файл `.env`:

```env
API_KEY=sk-ваш-ключ-openai
MODEL=gpt-4o-mini
DATABASE_URL=postgresql+psycopg2://postgres:пароль@localhost:5432/ai_chat
SECRET_KEY=ваш-секретный-ключ
```

Установите зависимости и примените миграции:

```bash
pip install -r requirements.txt
alembic upgrade head
```

Запустите сервер:

```bash
uvicorn app.main:app --reload
```

Бэкенд: http://127.0.0.1:8000  
Документация API: http://127.0.0.1:8000/docs

### 3. Фронтенд

В новом терминале:

```bash
cd frontend
npm install
npm run dev
```

Фронтенд: http://localhost:5173

## Основные возможности

- Регистрация и авторизация (JWT + refresh-токены)
- Роли пользователей: guest, wanderer, expert, legend, admin
- Создание и редактирование персонажей
- Чаты с персонажами (стриминг ответов)
- История диалогов
- Профиль пользователя с балансом

## Структура проекта

```
backend/
├── app/
│   ├── models/       # SQLAlchemy модели
│   ├── schemas/      # Pydantic схемы
│   ├── routers/      # Эндпоинты
│   ├── security.py   # JWT и хеширование паролей
│   └── main.py
├── alembic/          # Миграции базы данных
└── requirements.txt

frontend/
├── src/
│   ├── pages/        # Login, Register, Profile
│   ├── App.jsx       # Интерфейс чата
│   └── api.js        # Работа с токенами и запросами
└── package.json
```
```