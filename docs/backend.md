# Backend Services & API Contracts

This document dives into the FastAPI application that powers the OSM Manager
API. It explains the layout, the major service classes, and endpoint behaviour
that other components rely on.

## Module Overview

| Module                              | Responsibility                                                                                                  |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `app/main.py`                       | FastAPI app factory, middleware, router inclusion, Prometheus instrumentation.                                  |
| `app/api/routes/`                   | Per-domain routers (`databases`, `imports`, `jobs`, `replication`, `metrics`, `health`).                        |
| `app/services/database_manager.py`  | All database lifecycle operations, PostGIS extension management, statistics, cached bounds.                     |
| `app/services/job_service.py`       | Job persistence helper used by both the web layer (async) and workers (sync).                                   |
| `app/utils/osm2pgsql.py`            | Safe wrapper constructing osm2pgsql command lines and handling download staging.                                |
| `app/workers/`                      | Celery tasks (`tasks.py`) and Celery configuration (`celery_app.py`).                                            |
| `app/models/`                       | SQLAlchemy 2.0 declarative models representing metadata tables.                                                 |
| `app/schemas/`                      | Pydantic models for request/response validation.                                                                |

## Request Flow

1. **Middleware** – All requests pass through `add_request_id` (injects
   `X-Request-ID` and records latency/metrics) and the SlowAPI rate limiter.
2. **Router / Dependency injection** – Route handlers request a scoped
   `AsyncSession` via `Depends(get_db_session)` and, for admin endpoints, the
   `verify_admin_token` dependency.
3. **Service call** – Routers delegate almost immediately to service classes
   (`DatabaseManagerService`, `AsyncJobService`).
4. **Response** – Pydantic schemas ensure consistent JSON, error handling is
   normalised through `HTTPException`.

## Key Endpoints

### Databases

- `GET /databases` – List managed databases with stored bounds and job pointers.
- `POST /databases` – Create metadata + physical database (admin token required).
- `DELETE /databases/{name}` – Terminate active connections, drop the DB.
- `GET /databases/{name}/stats` – Returns size in bytes and table count.
- `GET /databases/{name}/bounds` – Cached geographic bounds in WGS‑84.
- `GET /databases/{name}/style` – Returns the inline style definition that was last used during import.
- `POST /databases/{name}/extensions` – Enable PostGIS/Hstore or other allowed extensions.

### Imports

- `POST /imports` – Enqueue an import job (create/append).
- `GET /imports/{job_id}` – Alias of `GET /jobs/{job_id}`.

### Jobs

- `GET /jobs` – Paginated job list, sorted by `created_at DESC`.
- `GET /jobs/{job_id}` – Detailed view including status, params, duration.
- `GET /jobs/{job_id}/logs` – Tail of structured log entries.
- `POST /jobs/{job_id}/retry` – Clones params into a new job (imports only).

### Replication

- `POST /replication/config` – Upsert replication settings for a database.
- `GET /replication/config` – Fetch configuration (used by UI).
- `POST /replication/update` – Enqueue a replication job for a target.

### Observability and Health

- `GET /health` – Readiness probe.
- `GET /metrics` – Prometheus exporter.

## DatabaseManagerService Highlights

- **Creation** – Validates logical name, creates `osm_<name>` via admin DSN,
  enables extensions, and caches the admin/user DSNs in metadata.
- **Deletion** – Terminates connections with `pg_terminate_backend`, runs
  `DROP DATABASE`, removes metadata.
- **Bounds caching** – First returns stored bounds if present. If missing,
  calls `_calculate_bounds` which:
  * Reads aggregated extents from `planet_osm_point` (fast path).
  * Falls back to `planet_osm_polygon`, `planet_osm_line`, `planet_osm_roads`
    if points are absent.
  * Stores the result on `ManagedDatabase`.

## Job Service Highlights

- **Async variant** – Used by API routes; immediately commits job creation so
  the worker can pick it up.
- **Sync variant** – Worker helper that atomically updates job status, duration,
  logs, and error information without leaving open transactions.

## Celery Worker Notes

- `jobs.run_import`
  * Builds `Osm2pgsqlOptions` from job params.
  * Streams logs to disk and `job_logs`.
  * Computes bounding box post-import and persists it.
  * Marks job success/failure with duration.
- `jobs.run_replication_update`
  * Placeholder stub (logs line, updates metadata); extend with real implementation.
- `jobs.schedule_replication_updates`
  * Beat scheduler iterating `replication_configs`, enqueuing updates respecting
    `dry_run`/`catch_up`.

## Error Handling Conventions

- Business logic raises `ValueError` for 4xx-worthy issues; routers catch them
  and wrap in `HTTPException`.
- Unexpected errors bubble up; uvicorn logs them and return 500s with request ID.
- Validation errors use FastAPI's handler patched to return JSON-serialisable
  payloads (FastAPI 0.110 introduced change in error structure).

## Security Considerations

- Admin endpoints must include `X-API-KEY`; the token lives in
  `OSM_MANAGER__SECURITY__ADMIN_API_TOKEN`.
- All database names are normalised to lowercase `[a-z0-9_]+` and prefixed. No
  raw user input enters SQL queries; all statements use parameters.
- `admin_dsn` is never exposed in API responses; only `primary_dsn` (masked in
  UI) is stored.

## Extending the API

1. Define request/response schemas in `app/schemas`.
2. Implement business logic in a service layer; keep routers thin.
3. When adding tables/columns, generate Alembic migrations (`alembic revision`).
4. Wire the router in `app/main.py` and document new endpoints in `/docs` or
   the dedicated docs modules.

For more precise details on the import pipeline, refer to
`docs/import-pipeline.md`, and for geographic bounds logic, read
`docs/bounding-boxes.md`.
