from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType
from app.models.manager import Job, JobLog

LOGGER = structlog.get_logger(__name__)


class AsyncJobService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = LOGGER.bind(component="AsyncJobService")

    async def create_job(
        self, job_type: JobType, target_db: str | None, params: dict[str, Any] | None
    ) -> Job:
        job = Job(type=job_type, target_db=target_db, params=params, status=JobStatus.pending)
        self.session.add(job)
        await self.session.flush()
        await self.session.commit()
        self.logger.info("job_created", job_id=str(job.id), job_type=job_type.value)
        return job

    async def get_job(self, job_id: str) -> Job:
        job = await self.session.get(Job, job_id)
        if not job:
            raise NoResultFound("Job not found")
        return job

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> tuple[int, list[Job]]:
        total_query = await self.session.execute(select(func.count()).select_from(Job))
        total = total_query.scalar_one()
        result = await self.session.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        )
        jobs = list(result.scalars().all())
        return total, jobs

    async def get_logs(self, job_id: str, limit: int = 200) -> list[JobLog]:
        result = await self.session.execute(
            select(JobLog)
            .where(JobLog.job_id == job_id)
            .order_by(JobLog.ts.desc(), JobLog.id.desc())
            .limit(limit)
        )
        logs = list(result.scalars().all())
        return list(reversed(logs))


class SyncJobService:
    def __init__(self, session: Session):
        self.session = session
        self.logger = LOGGER.bind(component="SyncJobService")

    def create_job(
        self, job_type: JobType, target_db: str | None, params: dict | None
    ) -> Job:
        job = Job(type=job_type, target_db=target_db, params=params or {})
        self.session.add(job)
        self.session.flush()
        self.logger.info("sync_job_created", job_id=str(job.id), job_type=job_type.value)
        return job

    def start_job(self, job_id: str) -> Job:
        job = self.session.get(Job, job_id)
        if not job:
            raise NoResultFound("Job not found")
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        self.session.add(job)
        self.session.flush()
        return job

    def finish_job(self, job_id: str, status: JobStatus, error_message: str | None = None) -> Job:
        job = self.session.get(Job, job_id)
        if not job:
            raise NoResultFound("Job not found")
        job.status = status
        job.finished_at = datetime.utcnow()
        if job.started_at:
            job.duration_ms = int(
                (job.finished_at - job.started_at).total_seconds() * 1000
            )
        if error_message:
            job.error_message = error_message
        self.session.add(job)
        self.session.flush()
        self.logger.info(
            "job_finished",
            job_id=str(job.id),
            status=status.value,
            error=bool(error_message),
        )
        return job

    def append_log(self, job_id: str, line: str) -> None:
        entry = JobLog(job_id=job_id, line=line)
        self.session.add(entry)
        self.session.flush()

    def mark_cancelled(self, job_id: str) -> None:
        job = self.session.get(Job, job_id)
        if not job:
            return
        job.status = JobStatus.cancelled
        job.cancelled = True
        job.finished_at = datetime.utcnow()
        self.session.add(job)
        self.session.flush()
