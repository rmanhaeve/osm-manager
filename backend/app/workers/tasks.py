from __future__ import annotations

import structlog
from celery import shared_task
import os
import subprocess
import httpx
import zipfile
from pathlib import Path
from psycopg import connect
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.session import get_sync_session
from app.models.enums import JobStatus, JobType
from app.models.manager import ManagedDatabase, ReplicationConfig
from app.services.job_service import SyncJobService
from app.utils.osm2pgsql import Osm2pgsqlOptions, run_osm2pgsql

LOGGER = structlog.get_logger(__name__)


def _physical_name(logical: str) -> str:
    return f"{settings.database.target_db_prefix}{logical}"


def _calculate_bounds_sync(full_name: str) -> dict[str, float] | None:
    """Compute a bounding box for the given physical DB inside the worker."""
    admin_url = make_url(settings.database.admin_psycopg_dsn).set(database=full_name)
    conninfo = admin_url.render_as_string(hide_password=False)
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

    with connect(conninfo) as conn:
        with conn.cursor() as cur:
            cur.execute(
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
            row = cur.fetchone()
            if row and row[0] is not None:
                return {
                    "min_lon": float(row[0]),
                    "min_lat": float(row[1]),
                    "max_lon": float(row[2]),
                    "max_lat": float(row[3]),
                }

            for table in tables:
                cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
                exists_row = cur.fetchone()
                if not exists_row or exists_row[0] is None:
                    continue
                cur.execute(
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
                row = cur.fetchone()
                if not row or row[0] is None:
                    continue
                x_min, y_min, x_max, y_max = row
                if None in row:
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


def _resolve_resource(path: str, log_dir: Path) -> str:
    """Return a local filesystem path for the given resource, downloading if remote."""
    if path.startswith(("http://", "https://")):
        filename = Path(path).name or "resource"
        target = log_dir / filename
        with httpx.stream("GET", path, timeout=None, follow_redirects=True) as response:
            response.raise_for_status()
            with target.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
        return str(target)

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = settings.filesystem.root / path.lstrip("/")
    if not candidate.exists():
        raise FileNotFoundError(f"Resource not found at {candidate}")
    return str(candidate)


def _import_water_polygons(
    *,
    water_path: str,
    database_name: str,
    log_dir: Path,
    options: Osm2pgsqlOptions,
    job_service: SyncJobService,
    job_id: str,
) -> bool:
    job_service.append_log(job_id, "Coastlines: loading water polygons dataset.")
    try:
        local_path = _resolve_resource(water_path, log_dir)
    except Exception as exc:
        job_service.append_log(job_id, f"Coastlines: unable to resolve water dataset ({exc}).")
        LOGGER.exception("coastline_water_resolution_failed", job_id=job_id)
        return False

    data_source = local_path
    if local_path.lower().endswith(".zip"):
        try:
            with zipfile.ZipFile(local_path) as archive:
                shapefile = next((name for name in archive.namelist() if name.lower().endswith(".shp")), None)
        except Exception as exc:  # noqa: BLE001
            job_service.append_log(job_id, f"Coastlines: invalid zip archive ({exc}).")
            LOGGER.exception("coastline_water_zip_failed", job_id=job_id)
            return False
        if not shapefile:
            job_service.append_log(job_id, "Coastlines: no shapefile found in water dataset.")
            return False
        data_source = f"/vsizip/{local_path}/{shapefile}"

    password_fragment = f" password={options.password}" if options.password else ""
    pg_conn = (
        f"PG:host={options.host} port={options.port} user={options.username}"
        f"{password_fragment} dbname={database_name}"
    )
    env = os.environ.copy()
    if options.password:
        env["PGPASSWORD"] = options.password
    try:
        subprocess.run(
            [
                "ogr2ogr",
                "-f",
                "PostgreSQL",
                pg_conn,
                data_source,
                "-nln",
                "coastline_water",
                "-overwrite",
            ],
            check=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        job_service.append_log(job_id, f"Coastlines: failed to import water polygons ({exc}).")
        LOGGER.exception("coastline_water_import_failed", job_id=job_id)
        return False
    return True


def _import_coastlines(
    *,
    source_path: str,
    database_name: str,
    log_dir: Path,
    options: Osm2pgsqlOptions,
    job_service: SyncJobService,
    job_id: str,
    mode: str,
    water_path: str | None,
) -> bool:
    """Generate coastline polygons or load existing water polygons."""
    if mode == "water":
        if not water_path:
            job_service.append_log(job_id, "Coastlines: water polygons path not provided.")
            return False
        return _import_water_polygons(
            water_path=water_path,
            database_name=database_name,
            log_dir=log_dir,
            options=options,
            job_service=job_service,
            job_id=job_id,
        )

    coastline_db = log_dir / "coastlines.sqlite"
    job_service.append_log(job_id, "Coastlines: generating polygons with osmcoastline.")
    try:
        subprocess.run(
            [
                "osmcoastline",
                "--output-database",
                str(coastline_db),
                "--gdal-driver",
                "SQLite",
                "--output-polygons=both",
                "--overwrite",
                source_path,
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        job_service.append_log(job_id, f"Coastlines: osmcoastline failed ({exc}).")
        LOGGER.exception("coastline_generation_failed", job_id=job_id)
        return False

    password_fragment = f" password={options.password}" if options.password else ""
    pg_conn = (
        f"PG:host={options.host} port={options.port} user={options.username}"
        f"{password_fragment} dbname={database_name}"
    )
    env = os.environ.copy()
    if options.password:
        env["PGPASSWORD"] = options.password

    for layer, target in (("land_polygons", "coastline_land"), ("water_polygons", "coastline_water")):
        job_service.append_log(job_id, f"Coastlines: importing {layer} into {target}.")
        try:
            subprocess.run(
                [
                    "ogr2ogr",
                    "-f",
                    "PostgreSQL",
                    pg_conn,
                    str(coastline_db),
                    layer,
                    "-nln",
                    target,
                    "-overwrite",
                ],
                check=True,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            job_service.append_log(job_id, f"Coastlines: failed to import {layer} ({exc}).")
            LOGGER.exception("coastline_import_failed", job_id=job_id, layer=layer)
            return False

    return True


@shared_task(name="jobs.run_import", bind=True)
def run_import(self, job_id: str) -> None:
    """Celery task that runs osm2pgsql and records job metadata/bounds."""
    with get_sync_session() as session:
        job_service = SyncJobService(session)
        job = job_service.start_job(job_id)
        managed: ManagedDatabase | None = session.get(ManagedDatabase, job.target_db)  # type: ignore[arg-type]
        if not managed:
            job_service.finish_job(job_id, JobStatus.failed, "Managed database missing")
            return

        url = make_url(managed.dsn)
        options_kwargs = dict(
            database_name=_physical_name(managed.name),
            username=url.username or "app_user",
            password=url.password,
            host=url.host or "localhost",
            port=url.port or 5432,
            mode=job.params.get("mode", "create") if job.params else "create",
            slim=job.params.get("slim", True) if job.params else True,
            hstore=job.params.get("hstore", True) if job.params else True,
            cache_mb=job.params.get("cache_mb", settings.worker_limits.default_cache_mb) if job.params else settings.worker_limits.default_cache_mb,
            number_processes=job.params.get("number_processes", settings.worker_limits.parallel_workers) if job.params else settings.worker_limits.parallel_workers,
            input_path=job.params.get("pbf_path") if job.params else None,
            input_url=job.params.get("pbf_url") if job.params else None,
            extra_args=tuple(job.params.get("extra_args", [])) if job.params else (),
        )

        log_dir = settings.filesystem.logs_dir / str(job_id)
        log_dir.mkdir(parents=True, exist_ok=True)

        style_definition = job.params.get("style_definition") if job.params else None
        if style_definition:
            style_path = log_dir / "import.style"
            Path(style_path).write_text(style_definition)
            options_kwargs["style_path"] = str(style_path)

        options = Osm2pgsqlOptions(**options_kwargs)

        log_path = log_dir / "import.log"

        def log_callback(line: str) -> None:
            job_service.append_log(job_id, line)

        include_coastlines = bool(job.params.get("include_coastlines") if job.params else False)

        try:
            exit_code, source_path = run_osm2pgsql(options, log_path, line_callback=log_callback)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("import_failed", job_id=job_id)
            job_service.append_log(job_id, f"ERROR: {exc}")
            job_service.finish_job(job_id, JobStatus.failed, str(exc))
            return

        if exit_code != 0:
            job_service.finish_job(job_id, JobStatus.failed, f"osm2pgsql exited with {exit_code}")
        else:
            job.log_path = str(log_path)
            managed.last_import_job_id = job.id
            bounds = _calculate_bounds_sync(_physical_name(managed.name))
            if bounds:
                managed.min_lon = bounds["min_lon"]
                managed.min_lat = bounds["min_lat"]
                managed.max_lon = bounds["max_lon"]
                managed.max_lat = bounds["max_lat"]
            if style_definition:
                managed.style_definition = style_definition

            if include_coastlines:
                coastline_source = (job.params.get("coastline_source") if job.params else None) or "extract"
                water_path = job.params.get("coastline_water_path") if job.params else None
                coast_ok = _import_coastlines(
                    source_path=source_path,
                    database_name=options.database_name,
                    log_dir=log_dir,
                    options=options,
                    job_service=job_service,
                    job_id=job_id,
                    mode=coastline_source,
                    water_path=water_path,
                )
                if not coast_ok:
                    job_service.finish_job(job_id, JobStatus.failed, "Coastline generation failed")
                    return

            job_service.finish_job(job_id, JobStatus.success)


@shared_task(name="jobs.run_replication_update", bind=True)
def run_replication_update(self, job_id: str) -> None:
    with get_sync_session() as session:
        job_service = SyncJobService(session)
        job = job_service.start_job(job_id)
        managed: ManagedDatabase | None = session.get(ManagedDatabase, job.target_db)  # type: ignore[arg-type]
        job_service.append_log(job_id, "Replication update stub executed.")
        if managed:
            managed.last_replication_job_id = job.id
        job_service.finish_job(job_id, JobStatus.success)
