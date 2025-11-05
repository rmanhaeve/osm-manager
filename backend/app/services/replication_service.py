from __future__ import annotations

import pathlib

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.manager import ManagedDatabase, ReplicationConfig
from app.schemas.replication import ReplicationConfigRequest

LOGGER = structlog.get_logger(__name__)


class ReplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = LOGGER.bind(component="ReplicationService")

    async def get_configs(self) -> list[ReplicationConfig]:
        result = await self.session.execute(select(ReplicationConfig))
        return list(result.scalars().all())

    async def get_config(self, target_db: str) -> ReplicationConfig | None:
        return await self.session.get(ReplicationConfig, target_db)

    async def upsert_config(self, payload: ReplicationConfigRequest) -> ReplicationConfig:
        managed = await self.session.get(ManagedDatabase, payload.target_db)
        if not managed:
            raise ValueError("Managed database not found")

        state_dir = settings.filesystem.state_dir / payload.target_db
        state_dir.mkdir(parents=True, exist_ok=True)
        state_path = state_dir / "state.txt"
        state_path.write_text("# state placeholder\n")

        existing = await self.get_config(payload.target_db)
        if existing:
            existing.base_url = str(payload.base_url)
            existing.replication_interval_minutes = payload.interval_minutes
            existing.dry_run = payload.dry_run
            existing.catch_up = payload.catch_up
            existing.state_path = str(state_path)
            self.session.add(existing)
            await self.session.commit()
            return existing

        config = ReplicationConfig(
            target_db=payload.target_db,
            base_url=str(payload.base_url),
            state_path=str(state_path),
            replication_interval_minutes=payload.interval_minutes,
            dry_run=payload.dry_run,
            catch_up=payload.catch_up,
        )
        self.session.add(config)
        await self.session.commit()
        self.logger.info("replication_config_saved", target_db=payload.target_db)
        return config
