
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
ADMIN_PASSWORD=замените-на-свой-пароль
```

`API_KEY`, `DATABASE_URL`, `SECRET_KEY` и `ADMIN_PASSWORD` нужны уже при импорте приложения. Пароль администратора по умолчанию не задаётся. Процесс не запускается, если `SECRET_KEY` или `ADMIN_PASSWORD` оставлены строками из `backend/.env.example`, и если логин и пароль — пара `admin` / `admin`. Имя и почта первого администратора по умолчанию: `admin` и `admin@example.com` (переменные `ADMIN_USERNAME`, `ADMIN_EMAIL`).

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

Страница ходит в API по пути `/api`. Dev-сервер Vite проксирует его на http://127.0.0.1:8000, так что сессия остаётся httpOnly cookie на том же сайте, что и страница. API принимает cookie-запросы только с origin фронтенда: по умолчанию `http://localhost:5173`, переопределение — `FRONTEND_ORIGIN`.

## Основные возможности

- Регистрация и авторизация (JWT в httpOnly cookie, обновление сессии при 401)
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