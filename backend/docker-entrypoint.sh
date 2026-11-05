#!/bin/sh
set -eu

python - <<'PY'
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(1)

last_error = "unknown"
for attempt in range(1, 31):
    print(f"Waiting for Postgres ({attempt}/30)...", flush=True)
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Postgres is ready.", flush=True)
        sys.exit(0)
    except Exception as exc:
        last_error = type(exc).__name__
        print(f"Postgres is not ready ({attempt}/30): {last_error}", flush=True)
        time.sleep(2)
    finally:
        engine.dispose()

print(f"Postgres did not become ready: {last_error}", file=sys.stderr)
sys.exit(1)
PY

echo "Applying database migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
