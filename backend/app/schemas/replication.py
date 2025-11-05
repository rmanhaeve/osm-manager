from __future__ import annotations

from datetime import datetime

from pydantic import AnyHttpUrl, Field

from .base import APIModel


class ReplicationConfigRequest(APIModel):
    target_db: str
    base_url: AnyHttpUrl
    interval_minutes: int = Field(5, ge=1, le=1440)
    dry_run: bool = False
    catch_up: bool = False


class ReplicationConfigResponse(APIModel):
    target_db: str
    base_url: AnyHttpUrl
    state_path: str
    interval_minutes: int
    dry_run: bool
    catch_up: bool
    last_sequence_number: int | None = None
    last_timestamp: datetime | None = None


class ReplicationTriggerRequest(APIModel):
    target_db: str
    dry_run: bool = False
    catch_up: bool = False


class ReplicationTriggerResponse(APIModel):
    job_id: str
    status: str
