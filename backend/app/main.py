from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.routes import databases, health, imports, jobs, metrics, replication
from app.core.config import settings
from app.core.logging import setup_logging
from app.observability.metrics import api_metrics

setup_logging()

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.security.rate_limit])

app = FastAPI(title="OSM Manager API", version="0.1.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):  # type: ignore[override]
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start
    api_metrics.request_latency.labels(request.method, request.url.path).observe(duration)
    api_metrics.requests_total.labels(request.method, request.url.path, str(response.status_code)).inc()
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:  # type: ignore[override]
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded", "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[override]
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(databases.router)
app.include_router(imports.router)
app.include_router(replication.router)
app.include_router(jobs.router)


@app.get("/tiles/{z}/{x}/{y}")
async def tile_stub(z: int, x: int, y: int) -> JSONResponse:
    return JSONResponse({"z": z, "x": x, "y": y, "message": "Tile rendering not yet implemented"})
