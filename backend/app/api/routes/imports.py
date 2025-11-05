from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_job_service, verify_admin_token
from app.models.enums import JobType
from app.schemas.imports import ImportRequest, ImportResponse
from app.schemas.jobs import JobResponse
from app.services.database_manager import DatabaseManagerService
from app.services.job_service import AsyncJobService
from app.workers.tasks import run_import

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportResponse, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_admin_token)])
async def start_import(
    payload: ImportRequest,
    session: AsyncSession = Depends(get_db_session),
    jobs: AsyncJobService = Depends(get_job_service),
) -> ImportResponse:
    db_service = DatabaseManagerService(session)
    record = await db_service.get_database(payload.target_db)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target database not found")

    job = await jobs.create_job(
        JobType.import_job,
        payload.target_db,
        payload.model_dump(mode="json"),
    )
    run_import.delay(str(job.id))
    return ImportResponse(job_id=str(job.id), status=job.status.value)


@router.get("/{job_id}", response_model=JobResponse)
async def import_status(
    job_id: str,
    jobs: AsyncJobService = Depends(get_job_service),
) -> JobResponse:
    job = await jobs.get_job(job_id)
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
