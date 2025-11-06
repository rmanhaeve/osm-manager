# Import & Replication Pipeline

This document outlines the lifecycle of an osm2pgsql import job, the moving parts
in the codebase, and how replication fits into the longer-term maintenance story.

## Import Lifecycle

1. **User request** (`POST /imports`)
   - Payload includes `target_db`, mode (`create` or `append`), and either
     `pbf_path` (local to `/data/pbf`) or `pbf_url`.
   - Endpoint validates inputs (`ImportRequest` schema), resolves the logical
     database name, and writes a job row via `AsyncJobService.create_job`.
   - Celery enqueues `jobs.run_import(job_id)`.

2. **Worker execution** (`jobs.run_import`)
   - Fetches the job, loads metadata for the target DB, and builds an
     `Osm2pgsqlOptions` instance. Important safeguards:
       * Options whitelist ensures only known flags are passed.
       * Credentials are provided via environment (`PGPASSWORD`) rather than CLI.
       * Remote PBFs are streamed to `/data/pbf/<filename>`; redirects are followed.
   - A line callback streams `stdout` to `job_logs` for real-time log viewing.
   - Upon completion:
       * Non-zero exit codes mark the job `failed` with captured message.
       * Success stores the log path, updates `last_import_job_id`, and calls
         `_calculate_bounds_sync` to persist geographic bounds on `ManagedDatabase`.
   - Bound computation first attempts to use `planet_osm_point` (fast,
     accurate for extracts), then falls back to polygon/line/road tables if no
     points exist. Results are stored in WGS‑84.

3. **Frontend feedback**
   - `/jobs` polls job status. `/jobs/{id}/logs` shows streaming output.
   - `/databases` reflects new `last_import_job_id` and cached bounds, allowing
     the map preview to zoom without recomputing expensive extents.
   - If “Generate coastline polygons” is checked during import:
     - In **extract** mode, `osmcoastline` runs against the downloaded PBF and imports
       `coastline_land` / `coastline_water` layers.
     - In **water file** mode, a remote or local water-polygons dataset (defaulting to
       the Geofabrik download) is pulled in via `ogr2ogr` and stored as `coastline_water`.

## Error Handling

- Job status transitions follow `pending → running → success|failed`.
- Retries clone the original job parameters and queue a fresh job.
- In case of download errors (HTTP status ≥ 400), the worker raises a
  descriptive message stored in `job.error_message`.

## Replication Lifecycle

Replication is currently a placeholder scaffold but the data flow is prepared:

1. **Configuration** (`POST /replication/config`)
   - Stores `base_url`, optional `state_path`, cadence, and dry-run flags.
2. **Scheduling**
   - Celery Beat invokes `jobs.schedule_replication_updates`, which iterates
     through active configs and enqueues `jobs.run_replication_update`.
3. **Update Task**
   - Stub logs a message and updates `last_replication_job_id`. Extend this task
     to call `osm2pgsql --append` with diffs and maintain replication state.
4. **State Tracking**
   - `replication_configs` keeps the last sequence number and timestamp; the
     planned extension is to maintain diff state files under `/data/state/<db>`.

## Persisted Artifacts

| Path / Table                       | Contents                                                     |
| --------------------------------- | ------------------------------------------------------------ |
| `/data/logs/<job_id>/import.log`  | Full osm2pgsql stdout/stderr for auditing.                   |
| `job_logs`                        | A truncated, structured log for UI/monitoring.               |
| `managed_databases.min_lon...`    | Cached bounds in WGS‑84 derived post-import.                 |
| `jobs.params`                     | Original job payload (mode, cache, input information).       |

## Operational Considerations

- **Concurrency** – `settings.worker_limits.max_concurrent_imports` and
  Celery worker count should be tuned based on host resources. Each import
  may demand substantial CPU/RAM.
- **Disk usage** – `/data/pbf` can be cleaned periodically if imports retain
  a private copy elsewhere. Osm2pgsql `--drop` can be added to purge middle tables.
- **Admin DSN** – All DDL (create/drop/writing cached bounds) uses an admin
  DSN to avoid privilege issues; ensure rotations update both env vars and
  the worker.
- **Monitoring** – Prometheus metrics (`osm_manager_*` series) are exposed on
  `/metrics` and include job counts and latencies.

## Extending Imports

- **Custom styles** – Place `.style` files under `/data/styles/<name>.style`
  and pass a `style_path` parameter.
- **Custom extra args** – Only allowlisted prefixes are accepted; extend
  `ALLOWED_EXTRA_FLAGS` in `osm2pgsql.py` cautiously.
- **Post-processing** – Add additional steps after `run_osm2pgsql` (e.g. index
  rebuilds) inside the worker task; always respect job status transitions.

Consult `docs/bounding-boxes.md` for more detail on how the cached bounds are
derived and consumed by the UI.
