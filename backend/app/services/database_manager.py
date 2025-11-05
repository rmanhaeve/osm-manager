from __future__ import annotations

import re

import structlog
from psycopg import AsyncConnection
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.manager import ManagedDatabase
from app.schemas.databases import DatabaseCreateRequest, ExtensionResponse

LOGGER = structlog.get_logger(__name__)

DB_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def _validate_identifier(name: str) -> str:
    if not DB_NAME_RE.match(name):
        raise ValueError("Database name must contain lowercase letters, digits, or underscore only.")
    return name


class DatabaseManagerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = LOGGER.bind(component="DatabaseManagerService")

    @staticmethod
    def _full_db_name(name: str) -> str:
        return f"{settings.database.target_db_prefix}{name}"

    @staticmethod
    def _derive_dsn(base_name: str) -> str:
        url = make_url(str(settings.database.primary_dsn))
        return str(url.set(database=base_name))

    @staticmethod
    def _psycopg_conninfo(dsn: str) -> str:
        return str(make_url(dsn).set(drivername="postgresql"))

    async def list_databases(self) -> list[ManagedDatabase]:
        result = await self.session.execute(select(ManagedDatabase).order_by(ManagedDatabase.name))
        return list(result.scalars().all())

    async def get_database(self, name: str) -> ManagedDatabase | None:
        return await self.session.get(ManagedDatabase, name)

    async def create_database(self, payload: DatabaseCreateRequest) -> ManagedDatabase:
        logical_name = _validate_identifier(payload.name.lower())
        if await self.get_database(logical_name):
            raise ValueError("Database already registered.")

        full_name = self._full_db_name(logical_name)
        target_dsn = payload.dsn or self._derive_dsn(full_name)

        await self._create_database(full_name)

        managed_db = ManagedDatabase(
            name=logical_name,
            dsn=target_dsn,
            display_name=payload.display_name,
            description=payload.description,
            style_id=payload.style_id,
        )
        self.session.add(managed_db)
        await self.session.flush()
        await self.session.commit()
        self.logger.info("database_created", logical_name=logical_name, full_name=full_name)
        return managed_db

    async def delete_database(self, name: str) -> None:
        logical_name = _validate_identifier(name.lower())
        record = await self.get_database(logical_name)
        if not record:
            raise ValueError("Database not found.")

        await self._terminate_connections(record)
        await self._drop_database(self._full_db_name(logical_name))

        await self.session.delete(record)
        await self.session.commit()
        self.logger.info("database_deleted", logical_name=logical_name)

    async def enable_extension(self, name: str, extension: str) -> ExtensionResponse:
        logical_name = _validate_identifier(name.lower())
        record = await self.get_database(logical_name)
        if not record:
            raise ValueError("Database not found.")

        full_name = self._full_db_name(logical_name)
        async with await AsyncConnection.connect(settings.database.admin_psycopg_dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(f'SET search_path = "public";')
                await cur.execute(f'SELECT 1 FROM pg_database WHERE datname = %s', (full_name,))
                row = await cur.fetchone()
                if not row:
                    raise RuntimeError("Physical database missing.")
        enable_query = f'CREATE EXTENSION IF NOT EXISTS "{extension}"'
        async with await AsyncConnection.connect(self._psycopg_conninfo(self._derive_dsn(full_name))) as conn:
            async with conn.cursor() as cur:
                await cur.execute(enable_query)
                await conn.commit()
        version = await self._fetch_extension_version(full_name, extension)
        return ExtensionResponse(database=logical_name, extension=extension, installed=True, version=version)

    async def _fetch_extension_version(self, db_name: str, extension: str) -> str | None:
        query = "SELECT extversion FROM pg_extension WHERE extname = %s"
        async with await AsyncConnection.connect(
            self._psycopg_conninfo(self._derive_dsn(db_name))
        ) as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (extension,))
                row = await cur.fetchone()
                return row[0] if row else None

    async def _create_database(self, full_name: str) -> None:
        admin_dsn = settings.database.admin_psycopg_dsn
        async with await AsyncConnection.connect(admin_dsn) as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (full_name,))
                if await cur.fetchone():
                    raise ValueError("Database already exists physically.")
            await conn.commit()
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(f'CREATE DATABASE "{full_name}" TEMPLATE template0')
                await cur.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{full_name}" TO app_user')

    async def _drop_database(self, full_name: str) -> None:
        admin_dsn = settings.database.admin_psycopg_dsn
        async with await AsyncConnection.connect(admin_dsn) as conn:
            await conn.set_autocommit(True)
            async with conn.cursor() as cur:
                await cur.execute(f'DROP DATABASE IF EXISTS "{full_name}"')

    async def _terminate_connections(self, record: ManagedDatabase) -> None:
        admin_dsn = settings.database.admin_psycopg_dsn
        db_name = self._full_db_name(record.name)
        async with await AsyncConnection.connect(admin_dsn) as conn:
            kill_sql = """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = %s AND pid <> pg_backend_pid()
            """
            async with conn.cursor() as cur:
                await cur.execute(kill_sql, (db_name,))
                await conn.commit()

    async def get_database_stats(self, name: str) -> dict[str, int | None]:
        logical_name = _validate_identifier(name.lower())
        full_name = self._full_db_name(logical_name)
        conninfo = settings.database.admin_psycopg_dsn
        async with await AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT pg_database_size(%s)", (full_name,))
                size_row = await cur.fetchone()
                await cur.execute(
                    """
                    SELECT count(*)
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND table_catalog = %s
                    """,
                    (full_name,),
                )
                table_row = await cur.fetchone()
        return {
            "size_bytes": int(size_row[0]) if size_row and size_row[0] is not None else None,
            "table_count": int(table_row[0]) if table_row and table_row[0] is not None else None,
        }
