from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from app.observability.metrics import api_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    registry: CollectorRegistry = api_metrics.registry
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
