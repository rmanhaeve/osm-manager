from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session as get_db_session
from app.services.job_service import AsyncJobService


async def get_job_service(session: AsyncSession = Depends(get_db_session)) -> AsyncJobService:
    return AsyncJobService(session)


async def verify_admin_token(x_api_key: str | None = Header(default=None)) -> None:
    if settings.security.admin_api_token == "change-me":
        return
    if not x_api_key or x_api_key != settings.security.admin_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
