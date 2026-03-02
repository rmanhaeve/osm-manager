from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery_app = Celery("osm_manager")
celery_app.conf.update(
    broker_url=settings.celery.broker_url,
    result_backend=settings.celery.result_backend,
    task_default_queue=settings.celery.task_default_queue,
    task_track_started=True,
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.workers"])
