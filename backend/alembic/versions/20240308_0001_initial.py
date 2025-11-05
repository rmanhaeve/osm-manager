"""Initial schema for OSM Manager."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20240308_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "styles",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
    )

    op.create_table(
        "managed_databases",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("dsn", sa.String(length=512), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_role", sa.String(length=64), nullable=True),
        sa.Column("read_role", sa.String(length=64), nullable=True),
        sa.Column("style_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_import_job_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_replication_job_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_size_bytes", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["style_id"], ["styles.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "jobs",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("type", sa.Enum("import", "replication", "vacuum_analyze", "compute_metrics", name="job_type"), nullable=False),
        sa.Column("target_db", sa.String(length=64), nullable=True),
        sa.Column("status", sa.Enum("pending", "running", "success", "failed", "cancelled", name="job_status"), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("log_path", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cancelled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["target_db"], ["managed_databases.name"], ondelete="SET NULL"),
    )

    op.create_table(
        "replication_configs",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("target_db", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column("state_path", sa.String(length=512), nullable=False),
        sa.Column("replication_interval_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("last_sequence_number", sa.Integer(), nullable=True),
        sa.Column("last_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("catch_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("force_one_shot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["target_db"], ["managed_databases.name"], ondelete="CASCADE"),
    )

    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("target_db", sa.String(length=64), nullable=True),
        sa.Column("total_size_bytes", sa.Integer(), nullable=True),
        sa.Column("import_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replication_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["target_db"], ["managed_databases.name"], ondelete="SET NULL"),
        sa.UniqueConstraint("metric_date", "target_db", name="uq_metrics_day_target"),
    )

    op.create_table(
        "job_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("line", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.CheckConstraint("char_length(line) <= 8192", name="ck_job_logs_line_length"),
    )


def downgrade() -> None:
    op.drop_table("job_logs")
    op.drop_table("metrics")
    op.drop_table("replication_configs")
    op.drop_table("jobs")
    op.drop_table("managed_databases")
    op.drop_table("styles")
    op.execute("DROP TYPE IF EXISTS job_type")
    op.execute("DROP TYPE IF EXISTS job_status")
