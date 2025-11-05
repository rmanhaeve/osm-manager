from __future__ import annotations

import structlog
from celery import shared_task
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


@shared_task(name="jobs.run_import", bind=True)
def run_import(self, job_id: str) -> None:
    with get_sync_session() as session:
        job_service = SyncJobService(session)
        job = job_service.start_job(job_id)
        managed: ManagedDatabase | None = session.get(ManagedDatabase, job.target_db)  # type: ignore[arg-type]
        if not managed:
            job_service.finish_job(job_id, JobStatus.failed, "Managed database missing")
            return

        url = make_url(managed.dsn)
        options = Osm2pgsqlOptions(
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
            style_path=job.params.get("style_path") if job.params else None,
            input_path=job.params.get("pbf_path") if job.params else None,
            input_url=job.params.get("pbf_url") if job.params else None,
            extra_args=tuple(job.params.get("extra_args", [])) if job.params else (),
        )

        log_dir = settings.filesystem.logs_dir / str(job_id)
        log_path = log_dir / "import.log"

        def log_callback(line: str) -> None:
            job_service.append_log(job_id, line)

        try:
            exit_code = run_osm2pgsql(options, log_path, line_callback=log_callback)
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


@shared_task(name="jobs.vacuum_analyze")
def vacuum_analyze(job_id: str) -> None:
    with get_sync_session() as session:
        job_service = SyncJobService(session)
        job = job_service.start_job(job_id)
        job_service.append_log(job_id, "Vacuum analyze placeholder executed.")
        job_service.finish_job(job_id, JobStatus.success)


@shared_task(name="jobs.compute_metrics")
def compute_metrics(job_id: str) -> None:
    with get_sync_session() as session:
        job_service = SyncJobService(session)
        job = job_service.start_job(job_id)
        job_service.append_log(job_id, "Metrics computation placeholder executed.")
        job_service.finish_job(job_id, JobStatus.success)


@shared_task(name="jobs.schedule_replication_updates")
def schedule_replication_updates() -> None:
    with get_sync_session() as session:
        job_service = SyncJobService(session)
        configs = session.query(ReplicationConfig).all()
        for config in configs:
            job = job_service.create_job(
                JobType.replication_job,
                config.target_db,
                {
                    "dry_run": config.dry_run,
                    "catch_up": config.catch_up,
                },
            )
            run_replication_update.delay(str(job.id))
