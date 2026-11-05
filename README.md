
```markdown
# AI Chat

Веб-приложение для общения с AI-персонажами.  
Бэкенд на FastAPI + PostgreSQL, фронтенд на React + Vite.

## Требования

Для обычного запуска:

- Docker с плагином Compose

Для запуска без Docker:

- Python 3.10+
- PostgreSQL
- Node.js (LTS)

## Установка и запуск

### Docker Compose

Из корня репозитория скопируйте пример окружения:

```bash
cp .env.example .env
```

`.env` в git не попадает. Задайте в нём свои `API_KEY`, `SECRET_KEY` и `ADMIN_PASSWORD`. Процесс не запускается, если `SECRET_KEY` или `ADMIN_PASSWORD` оставлены строками из `.env.example`, и если логин и пароль — пара `admin` / `admin`.

Имя базы, пользователь и пароль Postgres читаются из `POSTGRES_DB`, `POSTGRES_USER` и `POSTGRES_PASSWORD`. Если переменных нет, Compose подставляет локальные значения `ai_chat`, `ai_chat` и `ai_chat_local`. `DATABASE_URL` должен указывать на сервис `postgres` и те же учётные данные (образец в `.env.example`). В контейнер бэкенда также передаются `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`, `API_KEY` и `FRONTEND_ORIGIN`.

```bash
docker compose up --build
```

Уже собранные образы поднимаются той же командой без `--build`.

- `postgres` — PostgreSQL 16. Данные лежат в именованном томе `postgres_data` и сохраняются после перезапуска.
- `backend` — ждёт, пока Postgres принимает соединения, выполняет `alembic upgrade head`, затем запускает API. Схему создают только миграции Alembic.
- `frontend` — dev-сервер Vite. Браузер на хосте открывает страницу, а запросы `/api` Vite проксирует на `backend` внутри сети Compose. Сессия остаётся httpOnly cookie на том же сайте, что и страница.

Фронтенд: http://localhost:5173  
Бэкенд: http://127.0.0.1:8000

`FRONTEND_ORIGIN` по умолчанию `http://localhost:5173` — этот адрес и нужно открывать в браузере. API принимает cookie-запросы только с этого origin.

Остановить стек, не удаляя данные:

```bash
docker compose down
```

Сбросить базу (том `postgres_data` удаляется):

```bash
docker compose down -v
```

`/docs`, `/redoc` и `/openapi.json` выключены, пока в `.env` не задано `ENABLE_API_DOCS=true`.

### Без Docker

#### 1. База данных

Создайте базу в PostgreSQL:

```sql
CREATE DATABASE ai_chat;
```

#### 2. Бэкенд

```bash
cd backend
```

Создайте `backend/.env`. Compose читает отдельный `.env` в корне репозитория, и в нём хост базы — `postgres`:

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

`/docs`, `/redoc` и `/openapi.json` выключены, пока в `backend/.env` не задано `ENABLE_API_DOCS=true`. Без этого флага схема API не отдаётся.

#### 3. Фронтенд

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
docker-compose.yml    # Postgres, backend, frontend
.env.example          # образец .env для Compose (сам .env не коммитится)
backend/
├── Dockerfile
├── app/
│   ├── models/       # SQLAlchemy модели
│   ├── schemas/      # Pydantic схемы
│   ├── routers/      # Эндпоинты
│   ├── migrations/   # Миграции Alembic
│   ├── security.py   # JWT и хеширование паролей
│   └── main.py
├── alembic.ini
└── requirements.txt

frontend/
├── Dockerfile
├── src/
│   ├── pages/        # Login, Register, Profile
│   ├── App.jsx       # Интерфейс чата
│   └── api.js        # Работа с токенами и запросами
└── package.json
```
```