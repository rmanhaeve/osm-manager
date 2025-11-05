import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.enums import JobStatus, JobType
from app.models.manager import JobLog
from app.services.job_service import AsyncJobService, SyncJobService


@pytest.fixture
async def async_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_async_job_service(async_session: AsyncSession) -> None:
    service = AsyncJobService(async_session)
    job = await service.create_job(JobType.import_job, "test", {"mode": "create"})
    total, jobs = await service.list_jobs()
    assert total == 1
    assert jobs[0].id == job.id


def test_sync_job_service() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        service = SyncJobService(session)
        job = service.create_job(JobType.import_job, "test", {"mode": "create"})
        service.start_job(str(job.id))
        service.append_log(str(job.id), "starting")
        service.finish_job(str(job.id), JobStatus.success)
        logs = session.query(JobLog).filter_by(job_id=job.id).all()
        assert logs
