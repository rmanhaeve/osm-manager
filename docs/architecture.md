# Architecture

OSM Manager is a containerised monorepo that glues together a FastAPI backend,
Celery worker pool, Redis, PostGIS, and a Vite-powered React UI. This document
summarises the moving parts, how they communicate, and the conventions used to
keep runtime behaviour predictable.

```
                ┌──────────────────────────┐
                │  React + Vite Frontend  │
                │  (frontend/, port 5173) │
                └──────────────┬──────────┘
                               │ HTTP/JSON
                               ▼
 ┌───────────────────────────────────────────────────────────┐
 │                 FastAPI Backend (backend/app)              │
 │ ┌───────────────────────────────────────────────────────┐ │
 │ │ Routers (app/api/routes)                              │ │
 │ │  - /databases        lifecycle, stats, bounds         │ │
 │ │  - /imports          enqueue osm2pgsql jobs           │ │
 │ │  - /replication      replication configuration        │ │
 │ │  - /jobs             status, log streaming            │ │
 │ │  - /metrics          Prometheus exporter              │ │
 │ └───────────────────────────────────────────────────────┘ │
 │                         │ SQLAlchemy Engine               │
 │                ┌────────▼────────┐                        │
 │                │  Metadata DB    │                        │
 │                │  (osm_manager)  │                        │
 │                └────────┬────────┘                        │
 │                         │ Celery task dispatch            │
 └─────────────────────────┼─────────────────────────────────┘
                           │ Redis broker (redis://)
                           ▼
              ┌──────────────────────────────┐
              │ Celery Workers (backend/app) │
              │  - jobs.run_import           │
              │  - jobs.run_replication_*    │
              │  - jobs.compute_metrics      │
              └──────────────┬───────────────┘
                             │ psycopg3 (admin + app roles)
                             ▼
                   ┌───────────────────────┐
                   │ PostGIS (osm_*) DBs   │
                   │  + /data/ bind mounts │
                   └───────────────────────┘
```

## Core Services

| Service        | Responsibility                                                                           |
| -------------- | ---------------------------------------------------------------------------------------- |
| `api`          | FastAPI app with REST endpoints, rate limiting (SlowAPI), Prometheus metrics, logging.   |
| `worker`       | Celery worker pool used for osm2pgsql imports and background maintenance tasks.          |
| `beat`         | Celery Beat scheduler; periodically triggers replication tasks.                          |
| `postgres`     | PostGIS-enabled PostgreSQL instance. `osm_manager` stores metadata; per-import DBs are `osm_<name>`. |
| `redis`        | Celery broker/result backend, also reused for short-lived caching if needed.             |
| `frontend`     | React SPA providing a thin management UI and Leaflet preview.                            |

All containers share a `./data` bind mount whose structure is described in the
root README.

## Data Flow

1. **Database creation** – `POST /databases` registers metadata in `osm_manager`,
   creates a physical database via the admin DSN, enables PostGIS/hstore, and
   grants least-privilege access to `app_user`.
2. **Import request** – `POST /imports` records a job row inside `job` and queues
   `jobs.run_import` through Redis.
3. **Worker execution** – The worker container consumes the job, resolves the
   target DSN, runs `osm2pgsql`, captures logs to `/data/logs/<job_id>/import.log`,
   stores log fragments in `job_logs`, and updates the job status. A bounding
   box is computed and persisted so the API can return it without recomputing.
4. **Frontend polling** – The UI uses `/jobs`, `/jobs/{id}/logs`, and `/databases`
   to render job activity and database summaries. Selecting a database calls
   `/databases/{name}/bounds` (if not already cached) and zooms the map.
5. **Replication** – Celery Beat periodically enqueues replication jobs that
   update downstream databases and refresh the `replication_configs` state.

## Database Roles

| Role        | Permissions                                                                       |
| ----------- | --------------------------------------------------------------------------------- |
| `super_user`| Created via init script; used only for admin DDL (create/drop DB, enable extensions). |
| `app_user`  | Default role for queries and osm2pgsql imports. Granted usage/create on schemas.  |
| `app_readonly` | Optional read-only consumers (not actively used yet, but provisioned).         |

## Configuration Matrix

- `settings.database.primary_dsn` – SQLAlchemy DSN for the metadata catalogue.
- `settings.database.admin_dsn` – Elevated driver used for DDL against metadata
  and target databases.
- `settings.worker_limits` – Per-node safe defaults for parallel osm2pgsql runs.
- `settings.security` – API token and rate limiting knobs.

See `docs/backend.md` for deeper detail on configuration and request handling.

## Directory Layout Highlights

```
backend/app/
├── api/routes/           # FastAPI routers
├── core/                 # config, logging utilities
├── models/               # SQLAlchemy models
├── schemas/              # pydantic request/response models
├── services/             # business logic (database manager, job orchestration)
├── utils/osm2pgsql.py    # safe wrapper constructing commands
└── workers/              # Celery tasks + app bootstrap
```

```
frontend/src/
├── pages/                # Route-level components
├── components/           # Reusable UI widgets
├── hooks/useApi.ts       # Fetch wrapper honouring admin token
└── types/api.ts          # Shared TypeScript models
```

Each folder includes targeted documentation files referenced from this document.

## Extending the System

- **Additional services** – Add Celery tasks inside `app/workers/tasks.py`
  and register them in `app/workers/celery_app.py`.
- **New API routes** – Define pydantic schemas in `app/schemas`, add router
  modules under `app/api/routes`, and include them in `app/main.py`.
- **Frontend pages** – Create a page component, register the route in
  `frontend/src/App.tsx`, and consume the API via `useApi`.
- **Database migrations** – Use Alembic (already configured). Run
  `docker compose exec api alembic revision -m "message"` then
  `alembic upgrade head`.

This architecture deliberately separates database orchestration (synchronous,
admin DSN) from job execution (Celery), so long-running imports or replication
never block the HTTP request thread.
