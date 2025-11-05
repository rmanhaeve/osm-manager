from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False, populate_by_name=True)


T = TypeVar("T")


class PaginatedResponse(APIModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class MessageResponse(APIModel):
    message: str = Field(..., description="Human friendly message.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
