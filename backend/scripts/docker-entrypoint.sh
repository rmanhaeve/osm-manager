#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] waiting for database..."
python - <<'PY'
import asyncio
from app.core.config import settings
from psycopg import AsyncConnection

async def wait():
    last_error: Exception | None = None
    for attempt in range(30):
        try:
            conn = await asyncio.wait_for(
                AsyncConnection.connect(settings.database.admin_psycopg_dsn),
                timeout=3,
            )
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(2)
        else:
            await conn.close()
            return
    message = "Database not reachable after retries"
    if last_error:
        message = f"{message}: {last_error}"
    raise SystemExit(message)

asyncio.run(wait())
PY

echo "[entrypoint] applying database migrations..."
alembic upgrade head

echo "[entrypoint] starting process: $*"
exec "$@"
