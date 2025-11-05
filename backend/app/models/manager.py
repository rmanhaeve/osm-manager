from __future__ import annotations

from datetime import datetime
import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Enum,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INTERVAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus, JobType


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class ManagedDatabase(Base, TimestampMixin):
    __tablename__ = "managed_databases"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    dsn: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    read_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    style_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("styles.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_import_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    last_replication_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    last_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    style: Mapped["Style | None"] = relationship("Style")
    replication_config: Mapped["ReplicationConfig | None"] = relationship(
        "ReplicationConfig", back_populates="managed_database", cascade="all,delete"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="managed_database",
        cascade="all,delete-orphan",
        foreign_keys="Job.target_db",
    )


class ReplicationConfig(Base, TimestampMixin):
    __tablename__ = "replication_configs"

    target_db: Mapped[str] = mapped_column(
        ForeignKey("managed_databases.name", ondelete="CASCADE"), primary_key=True
    )
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    state_path: Mapped[str] = mapped_column(String(512), nullable=False)
    replication_interval_minutes: Mapped[int] = mapped_column(Integer, default=5)
    last_sequence_number: Mapped[int | None] = mapped_column(Integer)
    last_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    catch_up: Mapped[bool] = mapped_column(Boolean, default=False)
    force_one_shot: Mapped[bool] = mapped_column(Boolean, default=False)

    managed_database: Mapped[ManagedDatabase] = relationship(
        "ManagedDatabase", back_populates="replication_config"
    )


class Job(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "jobs"

    type: Mapped[JobType] = mapped_column(
        Enum(
            JobType,
            name="job_type",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    target_db: Mapped[str | None] = mapped_column(
        ForeignKey("managed_databases.name", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            name="job_status",
            native_enum=False,
            values_callable=_enum_values,
        ),
        default=JobStatus.pending,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    log_path: Mapped[str | None] = mapped_column(String(512))
    error_message: Mapped[str | None] = mapped_column(Text)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)

    managed_database: Mapped["ManagedDatabase | None"] = relationship(
        "ManagedDatabase", back_populates="jobs", foreign_keys=target_db
    )
    logs: Mapped[list["JobLog"]] = relationship(
        "JobLog", back_populates="job", cascade="all, delete-orphan"
    )


class JobLog(Base):
    __tablename__ = "job_logs"

    __table_args__ = (
        CheckConstraint("char_length(line) <= 8192", name="ck_job_logs_line_length"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    line: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped[Job] = relationship("Job", back_populates="logs")


class Style(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "styles"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(128))

    managed_databases: Mapped[list[ManagedDatabase]] = relationship(
        "ManagedDatabase", back_populates="style"
    )


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("metric_date", "target_db", name="uq_metrics_day_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    metric_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    target_db: Mapped[str | None] = mapped_column(
        ForeignKey("managed_databases.name", ondelete="SET NULL"), nullable=True
    )
    total_size_bytes: Mapped[int | None] = mapped_column(Integer)
    import_count: Mapped[int] = mapped_column(Integer, default=0)
    replication_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)

    managed_database: Mapped["ManagedDatabase | None"] = relationship("ManagedDatabase")
