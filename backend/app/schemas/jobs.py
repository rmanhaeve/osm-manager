from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .base import APIModel
from app.models.enums import JobStatus, JobType


class JobResponse(APIModel):
    id: str
    type: JobType
    target_db: str | None = None
    status: JobStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    params: dict | None = None
    log_path: str | None = None
    error_message: str | None = None


class JobListResponse(APIModel):
    total: int
    items: list[JobResponse]


class JobLogLine(APIModel):
    ts: datetime
    line: str = Field(..., description="Single log line.")


class JobLogResponse(APIModel):
    job_id: str
    lines: list[JobLogLine]
