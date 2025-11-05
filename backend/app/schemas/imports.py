from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, Field, validator

from .base import APIModel
from .databases import validate_db_identifier


class ImportRequest(APIModel):
    target_db: str = Field(..., description="Managed database name.")
    mode: Literal["create", "append"] = Field("create")
    pbf_path: str | None = Field(None, description="Path to local .pbf file.")
    pbf_url: AnyHttpUrl | None = Field(None, description="Remote .pbf download URL.")
    style_id: str | None = Field(None)
    slim: bool = Field(True)
    hstore: bool = Field(True)
    cache_mb: int = Field(2000, ge=64, le=16384)
    number_processes: int = Field(4, ge=1, le=16)
    extra_args: list[str] = Field(default_factory=list)
    dry_run: bool = Field(False)

    @validator("target_db")
    def validate_target_db(cls, value: str) -> str:
        return validate_db_identifier(value)

    @validator("extra_args", each_item=True)
    def validate_extra_args(cls, value: str) -> str:
        allowed_prefixes = ("--flat-nodes", "--tag-transform-script")
        if not value.startswith(allowed_prefixes):
            raise ValueError("Only whitelisted extra flags allowed.")
        return value

    @validator("pbf_path", always=True)
    def validate_source(cls, value: str | None, values: dict) -> str | None:
        if not value and not values.get("pbf_url"):
            raise ValueError("pbf_path or pbf_url must be provided")
        return value


class ImportResponse(APIModel):
    job_id: str
    status: str
