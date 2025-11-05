# Development & Operations Playbook

This guide collects day-to-day tasks for engineers maintaining OSM Manager:
environment setup, common commands, migrations, debugging, and deployment
considerations.

## Local Environment

### Prerequisites

- Docker & docker compose v2 (used for the default stack and tests).
- Python 3.11 (venv for backend development).
- Node.js 20 (frontend dev server).
- GNU Make is optional but convenient for scripting commands.

### Environment Variables

Copy `.env.example` to `.env`; the compose file reads values from there.
Important keys:

| Variable                               | Description                                         |
| ---------------------------------------| --------------------------------------------------- |
| `OSM_MANAGER__DATABASE__PRIMARY_DSN`   | Metadata DB DSN; adjust host/port per environment.  |
| `OSM_MANAGER__DATABASE__ADMIN_DSN`     | Elevated DSN for DDL operations.                     |
| `OSM_MANAGER__SECURITY__ADMIN_API_TOKEN` | Required for mutating API calls.                   |
| `VITE_ADMIN_TOKEN` (frontend)          | Mirrors the admin token for browser fetches.        |
| `VITE_POSTGRES_PORT` (frontend)        | Host-exposed Postgres port (defaults to `5433`).     |

## Running Services

```bash
docker compose up --build
```

The first run will initialise the metadata database, run Alembic migrations,
and start all services (postgres, redis, api, worker, beat, frontend).

### Backend (standalone)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Celery Workers

```bash
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

### Frontend Dev Server

```bash
cd frontend
npm install
npm run dev
```

## Database Migrations

1. Ship schema changes by generating an Alembic revision:
   ```bash
   docker compose exec api alembic revision -m "describe change"
   ```
2. Edit the revision file to include precise DDL.
3. Apply locally with `docker compose exec api alembic upgrade head`.
4. Commit both the migration and model changes.

## Useful Commands

| Task                              | Command                                                                 |
| --------------------------------- | ----------------------------------------------------------------------- |
| Tail worker logs                  | `docker compose logs -f worker`                                         |
| Inspect job logs                  | `docker compose exec postgres psql -U postgres -d osm_manager -c 'SELECT * FROM job_logs WHERE job_id=... ORDER BY ts;'` |
| Drop target DB manually           | `docker compose exec postgres psql -U postgres -c 'DROP DATABASE IF EXISTS osm_<name>;'` |
| Clear cached bounds               | `docker compose exec postgres psql -U postgres -d osm_manager -c 'UPDATE managed_databases SET min_lon=NULL, ...;'` |
| Rebuild frontend assets           | `npm run build`                                                         |
| Run backend tests                 | `cd backend && pytest`                                                  |

## Debugging Tips

- **request IDs** – Every API response includes `X-Request-ID`; correlate with logs.
- **osm2pgsql command** – Worker logs log the full command and exit codes. Inspect
  `/data/logs/<job_id>/import.log` for raw output.
- **PostgreSQL** – The metadata DB (`osm_manager`) captures audit fields
  (`created_at`, `updated_at`, job references). Use it to trace actions.
- **Bounds anomalies** – If a bounding box looks too large, re-run the job or
  truncate cached bounds; the point-first strategy should prevent large polygons
  from widening the box.

## Deployment Considerations

- **Secrets** – Replace the default API token and database passwords. Consider
  injecting them via Docker secrets or an env manager (Vault, AWS SSM).
- **Scaling** – Run additional Celery workers by scaling the `worker` service.
  Redis is sufficient for moderate loads; switch to RabbitMQ if you need
  stronger guarantees.
- **SSL/TLS** – Terminate TLS in front of the API (nginx, Traefik). Ensure CORS
  origins are configured via `OSM_MANAGER__SECURITY__ALLOWED_ORIGINS`.
- **Backups** – Regularly back up both `osm_manager` (metadata) and the managed
  PostGIS databases. PostgreSQL base backups or logical dumps are recommended.
- **Monitoring** – Scrape `/metrics` with Prometheus. Alert on job failure rates,
  replication lag, and worker queue sizes.

## Continuous Integration Ideas

- Run `pytest` inside the `backend` container.
- Build the frontend (`npm run build`) to catch type errors and linting issues.
- Execute integration tests (`tests/e2e/run_import.sh`) against disposable
  containers to validate the full pipeline.

For architectural context see `docs/architecture.md` and for API details visit
`docs/backend.md`.
