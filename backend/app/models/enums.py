from __future__ import annotations

import enum


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class JobType(str, enum.Enum):
    import_job = "import"
    replication_job = "replication"
