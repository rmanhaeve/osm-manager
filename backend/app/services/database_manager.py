"""Service helpers for managed PostGIS databases and metadata catalog.

Responsibilities covered here include database creation/deletion, extension
management, statistics gathering, and caching/retrieval of geographic bounds.
"""

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
    """High-level orchestration helper for metadata and target databases."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = LOGGER.bind(component="DatabaseManagerService")

    @staticmethod
    def _full_db_name(name: str) -> str:
        return f"{settings.database.target_db_prefix}{name}"

    @staticmethod
    def _derive_dsn(base_name: str) -> str:
        url = make_url(str(settings.database.primary_dsn))
        return url.set(database=base_name).render_as_string(hide_password=False)

    @staticmethod
    def _psycopg_conninfo(dsn: str) -> str:
        return make_url(dsn).set(drivername="postgresql").render_as_string(hide_password=False)

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

        admin_url = make_url(settings.database.admin_psycopg_dsn).set(database=full_name)
        target_conninfo = admin_url.render_as_string(hide_password=False)
        async with await AsyncConnection.connect(target_conninfo) as db_conn:
            await db_conn.set_autocommit(True)
            async with db_conn.cursor() as cur:
                await cur.execute('CREATE EXTENSION IF NOT EXISTS postgis')
                await cur.execute('CREATE EXTENSION IF NOT EXISTS hstore')
                await cur.execute('GRANT USAGE ON SCHEMA public TO app_user')
                await cur.execute('GRANT CREATE ON SCHEMA public TO app_user')

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
        admin_url = make_url(settings.database.admin_psycopg_dsn).set(database=full_name)
        target_conninfo = admin_url.render_as_string(hide_password=False)
        async with await AsyncConnection.connect(target_conninfo) as conn:
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

    async def get_database_bounds(self, name: str) -> dict[str, float] | None:
        logical_name = _validate_identifier(name.lower())
        record = await self.get_database(logical_name)
        if not record:
            raise ValueError("Database not found")

        if (
            record.min_lon is not None
            and record.min_lat is not None
            and record.max_lon is not None
            and record.max_lat is not None
        ):
            return {
                "min_lon": record.min_lon,
                "min_lat": record.min_lat,
                "max_lon": record.max_lon,
                "max_lat": record.max_lat,
            }

        bounds = await self._calculate_bounds(self._full_db_name(logical_name))
        if not bounds:
            return None

        record.min_lon = bounds["min_lon"]
        record.min_lat = bounds["min_lat"]
        record.max_lon = bounds["max_lon"]
        record.max_lat = bounds["max_lat"]
        self.session.add(record)
        await self.session.commit()
        return bounds

    async def _calculate_bounds(self, full_name: str) -> dict[str, float] | None:
        """Derive bounds for the target database using async psycopg connection."""
        target_conninfo = self._psycopg_conninfo(self._derive_dsn(full_name))
        tables = [
            "planet_osm_polygon",
            "planet_osm_line",
            "planet_osm_point",
            "planet_osm_roads",
        ]

        min_lon = float("inf")
        min_lat = float("inf")
        max_lon = float("-inf")
        max_lat = float("-inf")
        found = False

        async with await AsyncConnection.connect(target_conninfo) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT
                        MIN(ST_X(ST_Transform(way, 4326))),
                        MIN(ST_Y(ST_Transform(way, 4326))),
                        MAX(ST_X(ST_Transform(way, 4326))),
                        MAX(ST_Y(ST_Transform(way, 4326)))
                    FROM planet_osm_point
                    WHERE way IS NOT NULL
                    """
                )
                point_row = await cur.fetchone()
                if point_row and point_row[0] is not None:
                    return {
                        "min_lon": float(point_row[0]),
                        "min_lat": float(point_row[1]),
                        "max_lon": float(point_row[2]),
                        "max_lat": float(point_row[3]),
                    }

                for table in tables:
                    await cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
                    exists_row = await cur.fetchone()
                    if not exists_row or exists_row[0] is None:
                        continue
                    await cur.execute(
                        f"""
                        SELECT
                            ST_XMin(extent)::double precision,
                            ST_YMin(extent)::double precision,
                            ST_XMax(extent)::double precision,
                            ST_YMax(extent)::double precision
                        FROM (
                            SELECT ST_Extent(ST_Transform(way, 4326)) AS extent
                            FROM {table}
                            WHERE way IS NOT NULL
                        ) AS bounds
                        """
                    )
                    row = await cur.fetchone()
                    if not row or row[0] is None:
                        continue
                    x_min, y_min, x_max, y_max = row
                    if x_min is None or y_min is None or x_max is None or y_max is None:
                        continue
                    found = True
                    min_lon = min(min_lon, float(x_min))
                    min_lat = min(min_lat, float(y_min))
                    max_lon = max(max_lon, float(x_max))
                    max_lat = max(max_lat, float(y_max))

        if not found:
            return None

        return {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        }
