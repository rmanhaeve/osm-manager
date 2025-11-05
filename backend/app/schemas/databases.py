from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, validator

from .base import APIModel


ALLOWED_DB_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_")


def validate_db_identifier(name: str) -> str:
    if not name:
        raise ValueError("Database name is required")
    lowered = name.lower()
    if any(ch not in ALLOWED_DB_NAME_CHARS for ch in lowered):
        raise ValueError("Database name must contain only lowercase letters, numbers, or underscore")
    if len(lowered) > 60:
        raise ValueError("Database name must be <= 60 characters")
    return lowered


class DatabaseCreateRequest(APIModel):
    name: str = Field(..., description="Logical name without prefix.")
    dsn: str | None = Field(None, description="Optional external DSN override.")
    display_name: str | None = Field(None)
    description: str | None = Field(None)
    style_id: str | None = Field(None)

    @validator("name")
    def validate_name(cls, value: str) -> str:
        return validate_db_identifier(value)


class DatabaseResponse(APIModel):
    name: str
    dsn: str
    display_name: str | None = None
    description: str | None = None
    style_id: str | None = None
    is_active: bool
    last_import_job_id: str | None = None
    last_replication_job_id: str | None = None
    last_size_bytes: int | None = None
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DatabaseStats(APIModel):
    name: str
    size_bytes: int
    table_count: int
    last_vacuum: datetime | None = None


class ExtensionRequest(APIModel):
    extension: str = Field("postgis", pattern="^[a-z_]+$", description="Extension to enable.")


class ExtensionResponse(APIModel):
    database: str
    extension: str
    installed: bool
    version: str | None = None
