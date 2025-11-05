from __future__ import annotations

from datetime import date

from .base import APIModel


class MetricResponse(APIModel):
    metric_date: date
    target_db: str | None = None
    total_size_bytes: int | None = None
    import_count: int
    replication_count: int
    notes: str | None = None
