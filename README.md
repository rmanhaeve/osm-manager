# OSM Manager

OSM Manager is a production-ready starter kit for orchestrating **osm2pgsql** imports, PostGIS database lifecycle, and replication diffs through a secure web interface. The stack ships with a FastAPI backend, Celery workers, a Redis broker, a PostGIS-enabled PostgreSQL instance, and a React + Vite frontend – all wired together via docker compose.

## Architecture

- **FastAPI backend (`backend/app`)** – REST API for managing target databases, launching imports, replication runs, job history, and metrics. Uses SQLAlchemy 2.0 + psycopg3, pydantic settings, SlowAPI rate limiting, structured logging, and Prometheus metrics.
- **Celery workers (`backend/app/workers`)** – Long running jobs for osm2pgsql imports, replication updates, vacuum/housekeeping, and metrics aggregation. Logs stream to disk (`/data/logs/<job_id>`) and into the `job_logs` table.
- **PostgreSQL + PostGIS (`docker-compose` PostGIS image)** – Primary `osm_manager` metadata catalog plus dynamically managed target databases. Init script provisions least-privilege roles (`app_user`, `app_readonly`, `super_user`).
- **Redis** – Celery broker/result backend. Can be swapped for Redis Sentinel or RabbitMQ in production.
- **React + Vite frontend (`frontend`)** – Minimal management GUI with Databases, Imports, Replication, Jobs, and Settings pages, plus a Leaflet preview backed by a stub `/tiles` API.
- **Observability** – Structlog JSON logs, request IDs, Prometheus metrics endpoint (`/metrics`), and rate-limited mutating routes.

```
├── backend
│   ├── app
│   │   ├── api/… (routers)
│   │   ├── core/… (config, logging, security placeholder)
│   │   ├── models/… (SQLAlchemy models)
│   │   ├── services/… (db + job orchestration logic)
│   │   ├── utils/osm2pgsql.py (safe wrapper)
│   │   └── workers/… (Celery app + tasks)
│   ├── alembic/ (migrations)
│   ├── scripts/init-db.sh
│   └── requirements.txt
├── frontend (React + Vite UI)
├── tests/e2e/run_import.sh (Docker-based integration workflow)
├── tests/data/sample.osm.pbf (stub for pipelines)
└── docker-compose.yml
```

## Prerequisites

- Docker and docker compose v2
- Python 3.11+ (for local FastAPI dev)
- Node.js 20+ (for frontend hot reload when not using Docker)

## Quickstart (Docker Compose)

```bash
cp .env.example .env
docker compose build
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d

# verify services
curl http://localhost:8000/health
open http://localhost:5173
```

Default credentials come from `.env.example`; change `OSM_MANAGER__SECURITY__ADMIN_API_TOKEN` before exposing beyond localhost. Managed data directories live under `./data` (bind-mounted to `/data` in containers):

- `/data/pbf` – osm2pgsql input files
- `/data/styles` – per-database `.style` files
- `/data/logs/<job_id>` – job stdout/stderr capture (rotatable)
- `/data/state/<db>/state.txt` – replication checkpoints

## Running an Import

1. Copy a PBF into `data/pbf/` (or point to a remote URL when launching).
2. Create a target database via API or GUI:

   ```bash
   curl -X POST http://localhost:8000/databases \
     -H 'Content-Type: application/json' \
     -H 'X-API-KEY: change-me' \
     -d '{"name":"osm_test","display_name":"Test DB"}'
   ```

3. Enable PostGIS (optional via API/GUI):

   ```bash
   curl -X POST http://localhost:8000/databases/osm_test/extensions \
     -H 'Content-Type: application/json' \
     -H 'X-API-KEY: change-me' \
     -d '{"extension": "postgis"}'
   ```

4. Launch import:

   ```bash
   curl -X POST http://localhost:8000/imports \
     -H 'Content-Type: application/json' \
     -H 'X-API-KEY: change-me' \
     -d '{
       "target_db": "osm_test",
       "mode": "create",
       "pbf_path": "/data/pbf/sample.osm.pbf",
       "cache_mb": 2000,
       "number_processes": 4
     }'
   ```

5. Monitor progress on `/jobs` (GUI) or API:

   ```bash
   curl http://localhost:8000/jobs
   curl http://localhost:8000/jobs/<job_id>/logs
   ```

Import jobs use the safe wrapper (`app/utils/osm2pgsql.py`) which builds commands from an allowlist, injects credentials via environment variables, and streams stdout to both disk and the `job_logs` table.

## Replication Diffs

1. Save replication config:

   ```bash
   curl -X POST http://localhost:8000/replication/config \
     -H 'Content-Type: application/json' \
     -H 'X-API-KEY: change-me' \
     -d '{
       "target_db": "osm_test",
       "base_url": "https://download.geofabrik.de/europe/monaco-updates",
       "interval_minutes": 10,
       "dry_run": false,
       "catch_up": true
     }'
   ```

2. Trigger a manual update:

   ```bash
   curl -X POST http://localhost:8000/replication/update \
     -H 'Content-Type: application/json' \
     -H 'X-API-KEY: change-me' \
     -d '{"target_db": "osm_test"}'
   ```

3. Celery beat (`jobs.schedule_replication_updates`) automatically queues replication jobs using the configured interval. Each run updates `replication_configs.last_sequence_number`, persists `state.txt`, and logs output.

## TrueNAS Scale Deployment

A TrueNAS Scale-compatible compose file is provided at `docker-compose.truenas.yml`. This uses pre-built images from GitHub Container Registry and explicit host paths for persistent storage.

### Setup

1. Create the required directories on your TrueNAS pool:

   ```bash
   mkdir -p /mnt/pool/appdata/osm_mgr/{data,pgdata,redisdata}
   ```

2. Adjust the paths in `docker-compose.truenas.yml` to match your pool name if different from `pool`.

3. Update the passwords and API token before deploying:
   - `POSTGRES_PASSWORD`
   - `OSM_MANAGER__DATABASE__PRIMARY_DSN` and `ADMIN_DSN` passwords
   - `OSM_MANAGER__SECURITY__ADMIN_API_TOKEN`

4. In TrueNAS Scale, go to **Apps → Discover Apps → Custom App** and paste the contents of `docker-compose.truenas.yml` into the YAML configuration.

### Notes

- The compose file uses list-style environment variables (`- KEY=value`) for TrueNAS compatibility
- Named volumes are replaced with explicit host paths to ensure data persists on ZFS
- Images are pulled from `ghcr.io/rmanhaeve/osm-manager/backend` and `frontend`
- Health checks with `depends_on: condition:` are simplified since TrueNAS doesn't fully support them

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Celery Workers

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

## Testing

- **Unit tests:** `cd backend && pytest app/tests`
- **Integration stub:** `tests/e2e/run_import.sh` spins up docker compose, seeds the sample `.osm.pbf`, and queues an import (uses a non-realistic tiny stub file; replace with a genuine PBF for meaningful validation).
- **Smoke checks:** `curl http://localhost:8000/metrics` for Prometheus metrics, `curl http://localhost:8000/tiles/0/0/0` for the tile stub.

The backend tests exercise schema validation, job orchestration, and command construction. Extend the suite with database-backed integration cases once a PostGIS test container is available; the infrastructure is in place to plug in a dockerized PostgreSQL service for CI pipelines.

## Configuration

Environment variables use nested Pydantic settings, e.g.

| Variable | Purpose | Default |
| --- | --- | --- |
| `OSM_MANAGER__DATABASE__PRIMARY_DSN` | Metadata DB DSN (SQLAlchemy format) | `postgresql+psycopg://app_user:app_password@postgres:5432/osm_manager` |
| `OSM_MANAGER__DATABASE__ADMIN_DSN` | Elevated runner used for DDL (safe allowlist) | `postgresql+psycopg://super_user:super_password@postgres:5432/postgres` |
| `OSM_MANAGER__FILESYSTEM__ROOT` | Volume root (`/data`) | `/data` |
| `OSM_MANAGER__SECURITY__ADMIN_API_TOKEN` | Simple RBAC placeholder | `change-me` |
| `OSM_MANAGER__WORKER__MAX_CONCURRENT_IMPORTS` | Safety rail to limit imports | `2` |

See `backend/app/core/config.py` for the full catalog and defaults.

## Safety Rails & Security

- Web process performs DDL through `super_user` only for sanctioned operations (create/drop DBs, enabling extensions). Routine queries use `app_user`.
- Database names are validated against `[a-z0-9_]+` and prefixed with `osm_` to avoid collisions.
- osm2pgsql flags are whitelisted; extra args must match approved prefixes.
- Rate limiting powered by SlowAPI protects mutating routes (default `60/minute`).
- Structured logging with request IDs supports distributed tracing; adjust log level via `OSM_MANAGER__LOG_LEVEL`.

## Next Steps

- Implement actual PostGIS tile proxy or vector tile service for the Leaflet preview.
- Expand Celery tasks to honor per-DB locks, disk/memory pre-checks, and cancellation support (DB flag already available on `jobs.cancelled`).
- Wire authentication/authorization (OIDC, OAuth2) via the `core/security.py` placeholder.
- Add more comprehensive integration tests using a seeded PostGIS container and non-stub `.osm.pbf` fixtures.

## Documentation

- [Architecture](docs/architecture.md)
- [Backend services & API contracts](docs/backend.md)
- [Import & replication pipelines](docs/import-pipeline.md)
- [Bounding box derivation & map preview](docs/bounding-boxes.md)
- [Frontend structure & UI conventions](docs/frontend.md)
- [Development & operations playbook](docs/development.md)

Happy mapping!
