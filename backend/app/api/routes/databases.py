from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, verify_admin_token
from app.schemas.databases import (
    DatabaseCreateRequest,
    DatabaseResponse,
    DatabaseStats,
    ExtensionRequest,
    ExtensionResponse,
)
from app.services.database_manager import DatabaseManagerService

router = APIRouter(prefix="/databases", tags=["databases"])


def _to_response(record) -> DatabaseResponse:
    return DatabaseResponse(
        name=record.name,
        dsn=record.dsn,
        display_name=record.display_name,
        description=record.description,
        style_id=str(record.style_id) if record.style_id else None,
        is_active=record.is_active,
        last_import_job_id=str(record.last_import_job_id) if record.last_import_job_id else None,
        last_replication_job_id=str(record.last_replication_job_id) if record.last_replication_job_id else None,
        last_size_bytes=record.last_size_bytes,
        last_checked_at=record.last_checked_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("", response_model=list[DatabaseResponse])
async def list_databases(
    session: AsyncSession = Depends(get_db_session),
) -> list[DatabaseResponse]:
    service = DatabaseManagerService(session)
    records = await service.list_databases()
    return [_to_response(record) for record in records]


@router.post("", response_model=DatabaseResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin_token)])
async def create_database(
    payload: DatabaseCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> DatabaseResponse:
    service = DatabaseManagerService(session)
    try:
        record = await service.create_database(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_response(record)


@router.delete(
    "/{name}",
    dependencies=[Depends(verify_admin_token)],
)
async def delete_database(
    name: str,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    service = DatabaseManagerService(session)
    try:
        await service.delete_database(name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{name}/extensions", response_model=ExtensionResponse, dependencies=[Depends(verify_admin_token)])
async def enable_extension(
    name: str,
    payload: ExtensionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ExtensionResponse:
    service = DatabaseManagerService(session)
    try:
        return await service.enable_extension(name, payload.extension)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{name}/stats", response_model=DatabaseStats)
async def database_stats(
    name: str,
    session: AsyncSession = Depends(get_db_session),
) -> DatabaseStats:
    service = DatabaseManagerService(session)
    stats = await service.get_database_stats(name)
    record = await service.get_database(name)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found")
    return DatabaseStats(
        name=name,
        size_bytes=stats.get("size_bytes") or 0,
        table_count=stats.get("table_count") or 0,
    )
