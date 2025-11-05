from __future__ import annotations

import pathlib
from functools import lru_cache

from pydantic import Field, PostgresDsn, validator
from sqlalchemy.engine import make_url
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="osm_manager__database__", frozen=True)

    primary_dsn: PostgresDsn = Field(
        "postgresql+psycopg://app_user:app_password@localhost:5432/osm_manager"
    )
    admin_dsn: PostgresDsn = Field(
        "postgresql+psycopg://super_user:super_password@localhost:5432/postgres"
    )
    target_db_prefix: str = Field("osm_", description="Prefix appended to managed DBs.")

    @property
    def primary_async_dsn(self) -> str:
        return str(self.primary_dsn).replace("+psycopg://", "+psycopg_async://")

    @property
    def admin_async_dsn(self) -> str:
        return str(self.admin_dsn).replace("+psycopg://", "+psycopg_async://")

    @property
    def primary_psycopg_dsn(self) -> str:
        url = make_url(str(self.primary_dsn)).set(drivername="postgresql")
        return url.render_as_string(hide_password=False)

    @property
    def admin_psycopg_dsn(self) -> str:
        url = make_url(str(self.admin_dsn)).set(drivername="postgresql")
        return url.render_as_string(hide_password=False)


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="osm_manager__redis__", frozen=True)

    url: str = Field("redis://localhost:6379/0")


class CelerySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="osm_manager__celery__", frozen=True)

    broker_url: str = Field("redis://localhost:6379/0")
    result_backend: str = Field("redis://localhost:6379/1")
    task_default_queue: str = Field("default")
    beat_sync_seconds: int = Field(300)


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="osm_manager__security__", frozen=True)

    admin_api_token: str = Field("change-me")
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    rate_limit: str = Field("60/minute")


class FilesystemSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="osm_manager__filesystem__", frozen=True)

    root: pathlib.Path = Field(pathlib.Path("/data"))

    @property
    def pbf_dir(self) -> pathlib.Path:
        return self.root / "pbf"

    @property
    def styles_dir(self) -> pathlib.Path:
        return self.root / "styles"

    @property
    def logs_dir(self) -> pathlib.Path:
        return self.root / "logs"

    @property
    def state_dir(self) -> pathlib.Path:
        return self.root / "state"


class WorkerLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="osm_manager__worker__", frozen=True)

    max_concurrent_imports: int = Field(2, ge=1)
    max_concurrent_replications: int = Field(2, ge=1)
    default_cache_mb: int = Field(2000, ge=64)
    parallel_workers: int = Field(4, ge=1)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="osm_manager__",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    environment: str = Field("development")
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000)
    log_level: str = Field("INFO")
    metrics_enabled: bool = Field(True)

    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    celery: CelerySettings = CelerySettings()
    security: SecuritySettings = SecuritySettings()
    filesystem: FilesystemSettings = FilesystemSettings()
    worker_limits: WorkerLimitSettings = WorkerLimitSettings()

    @validator("environment")
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return value

    def ensure_directories(self) -> None:
        for directory in [
            self.filesystem.root,
            self.filesystem.pbf_dir,
            self.filesystem.styles_dir,
            self.filesystem.logs_dir,
            self.filesystem.state_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.ensure_directories()
    return settings


settings = get_settings()
