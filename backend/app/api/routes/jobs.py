from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_job_service, verify_admin_token
from app.models.enums import JobStatus, JobType
from app.schemas.jobs import JobListResponse, JobLogLine, JobLogResponse, JobResponse
from app.services.job_service import AsyncJobService
from app.workers.tasks import run_import

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_job_response(job) -> JobResponse:
    return JobResponse(
        id=str(job.id),
        type=job.type,
        target_db=job.target_db,
        status=job.status,
        started_at=job.started_at,
        finished_at=job.finished_at,
        duration_ms=job.duration_ms,
        params=job.params,
        log_path=job.log_path,
        error_message=job.error_message,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    jobs: AsyncJobService = Depends(get_job_service),
) -> JobListResponse:
    total, records = await jobs.list_jobs(limit=limit, offset=offset)
    return JobListResponse(total=total, items=[_to_job_response(record) for record in records])


@router.get("/{job_id}", response_model=JobResponse)
async def job_detail(job_id: str, jobs: AsyncJobService = Depends(get_job_service)) -> JobResponse:
    job = await jobs.get_job(job_id)
    return _to_job_response(job)


@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    dependencies=[Depends(verify_admin_token)],
)
async def retry_job(
    job_id: str,
    jobs: AsyncJobService = Depends(get_job_service),
) -> JobResponse:
    job = await jobs.get_job(job_id)
    if job.status not in {JobStatus.failed, JobStatus.cancelled}:
        raise HTTPException(status_code=400, detail="Only failed or cancelled jobs can be retried.")

    if job.type != JobType.import_job:
        raise HTTPException(status_code=400, detail=f"Retry not supported for job type '{job.type}'.")

    new_job = await jobs.create_job(JobType.import_job, job.target_db, job.params or {})
    run_import.delay(str(new_job.id))
    return _to_job_response(new_job)


@router.get("/{job_id}/logs", response_model=JobLogResponse)
async def job_logs(
    job_id: str,
    limit: int = Query(200, ge=10, le=2000),
    jobs: AsyncJobService = Depends(get_job_service),
) -> JobLogResponse:
    await jobs.get_job(job_id)
    lines = await jobs.get_logs(job_id, limit=limit)
    return JobLogResponse(
        job_id=job_id,
        lines=[JobLogLine(ts=entry.ts, line=entry.line) for entry in lines],
    )
