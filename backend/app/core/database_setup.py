"""Database initialization and role setup."""

from __future__ import annotations

import structlog
from psycopg import AsyncConnection

from app.core.config import settings

LOGGER = structlog.get_logger(__name__)


async def ensure_database_roles() -> None:
    """Ensure required PostgreSQL roles exist with proper privileges."""
    roles_sql = """
    DO $$
    BEGIN
       IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
          CREATE ROLE app_user LOGIN PASSWORD 'app_password';
       END IF;
       IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_readonly') THEN
          CREATE ROLE app_readonly LOGIN PASSWORD 'app_readonly';
       END IF;
       IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'super_user') THEN
          CREATE ROLE super_user WITH LOGIN PASSWORD 'super_password' SUPERUSER;
       END IF;
    END
    $$;
    
    GRANT CONNECT ON DATABASE osm_manager TO app_user, app_readonly, super_user;
    GRANT ALL PRIVILEGES ON DATABASE osm_manager TO app_user;
    GRANT USAGE ON SCHEMA public TO app_user, app_readonly, super_user;
    GRANT CREATE ON SCHEMA public TO app_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
    GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
    GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_readonly;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
    """
    
    try:
        # Connect using the postgres superuser to create roles
        admin_dsn = settings.database.admin_psycopg_dsn
        async with await AsyncConnection.connect(admin_dsn) as conn:
            # Execute role creation
            async with conn.cursor() as cur:
                await cur.execute(roles_sql)
            await conn.commit()
        LOGGER.info("database_roles_ensured")
    except Exception as exc:
        LOGGER.error("failed_to_ensure_roles", error=str(exc))
        raise
