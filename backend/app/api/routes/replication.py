from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_db_session, get_job_service, verify_admin_token
from app.schemas.replication import (
    ReplicationConfigRequest,
    ReplicationConfigResponse,
    ReplicationTriggerRequest,
    ReplicationTriggerResponse,
)
from app.services.replication_service import ReplicationService
from app.services.job_service import AsyncJobService
from app.models.enums import JobType
from app.workers.tasks import run_replication_update

router = APIRouter(prefix="/replication", tags=["replication"])


@router.get("/config", response_model=list[ReplicationConfigResponse])
async def list_replication_configs(session=Depends(get_db_session)) -> list[ReplicationConfigResponse]:
    service = ReplicationService(session)
    configs = await service.get_configs()
    return [
        ReplicationConfigResponse(
            target_db=config.target_db,
            base_url=config.base_url,
            state_path=config.state_path,
            interval_minutes=config.replication_interval_minutes,
            dry_run=config.dry_run,
            catch_up=config.catch_up,
            last_sequence_number=config.last_sequence_number,
            last_timestamp=config.last_timestamp,
        )
        for config in configs
    ]


@router.post("/config", response_model=ReplicationConfigResponse, dependencies=[Depends(verify_admin_token)])
async def save_replication_config(
    payload: ReplicationConfigRequest,
    session=Depends(get_db_session),
) -> ReplicationConfigResponse:
    service = ReplicationService(session)
    try:
        config = await service.upsert_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReplicationConfigResponse(
        target_db=config.target_db,
        base_url=config.base_url,
        state_path=config.state_path,
        interval_minutes=config.replication_interval_minutes,
        dry_run=config.dry_run,
        catch_up=config.catch_up,
        last_sequence_number=config.last_sequence_number,
        last_timestamp=config.last_timestamp,
    )


@router.post("/update", response_model=ReplicationTriggerResponse, dependencies=[Depends(verify_admin_token)])
async def trigger_replication(
    payload: ReplicationTriggerRequest,
    session=Depends(get_db_session),
    jobs: AsyncJobService = Depends(get_job_service),
) -> ReplicationTriggerResponse:
    service = ReplicationService(session)
    config = await service.get_config(payload.target_db)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Replication config missing")

    job = await jobs.create_job(
        JobType.replication_job,
        payload.target_db,
        {
            "dry_run": payload.dry_run,
            "catch_up": payload.catch_up,
        },
    )
    run_replication_update.delay(str(job.id))
    return ReplicationTriggerResponse(job_id=str(job.id), status=job.status.value)
