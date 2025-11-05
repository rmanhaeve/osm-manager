# Bounding Box Computation & Consumption

OSM Manager caches a geographic bounding box for each managed database to avoid
slow runtime queries. This document explains the motivation, the algorithm, and
how the cached values are used by the API and UI.

## Why Cache Bounds?

Calculating `ST_Extent` across tables with hundreds of thousands of features can
take several seconds and requires connecting to the target database. Doing this
for every `/databases/{name}/bounds` request (or map interaction) would be too
slow, particularly when targeting larger extracts.

By computing the bounds at import time and storing them on the metadata table
(`managed_databases`), subsequent requests become simple metadata lookups.

## Algorithm

1. **Fast path – Points**
   - Query:
     ```sql
     SELECT
       MIN(ST_X(ST_Transform(way, 4326))),
       MIN(ST_Y(ST_Transform(way, 4326))),
       MAX(ST_X(ST_Transform(way, 4326))),
       MAX(ST_Y(ST_Transform(way, 4326)))
     FROM planet_osm_point
     WHERE way IS NOT NULL;
     ```
   - If the table exists and returns values, use this as the bounding box.
     Point geometries already represent the densest set of features in most
     extracts and reflect the true extent without being distorted by large
     polygons that extend far beyond the area of interest (e.g. regions).

2. **Fallback – Polygons/Lines/Roads**
   - If no points are present, iterate through `planet_osm_polygon`,
     `planet_osm_line`, and `planet_osm_roads`.
   - For each table that exists, compute:
     ```sql
     SELECT ST_Extent(ST_Transform(way, 4326)) FROM <table> WHERE way IS NOT NULL;
     ```
   - Merge the resulting min/max lon/lat across tables.

3. **Storage**
   - The final envelope (min/max lon/lat in WGS‑84) is saved to the
     `managed_databases` row (`min_lon`, `min_lat`, `max_lon`, `max_lat`).
   - Bounds are only recalculated when a value is missing. Deleting the cached
     values (or `UPDATE managed_databases SET min_lon=NULL ...`) forces a
     recompute the next time `/databases/{name}/bounds` is called.

4. **Thread Safety**
   - Bounding boxes are computed synchronously within the Celery worker to avoid
     race conditions between multiple imports or API requests. The worker uses
     the admin DSN so it can always read the target database.

## API & UI Usage

- `GET /databases` includes the four cached values for convenience; the frontend
  picks them up when available and avoids an extra network request.
- `GET /databases/{name}/bounds` returns cached values if present; otherwise,
  it triggers the fallback calculation once and caches the result.
- The React frontend calls `showBounds([[min_lat,min_lon],[max_lat,max_lon]])`
  on a Leaflet map component, which both zooms the map and draws a rectangle.

## Edge Cases

- **Empty database** – If no geometries exist (fresh DB without imports),
  the API returns HTTP 404 for `/bounds` and the UI shows an error message.
- **Cross-border features** – The point-first strategy mitigates huge polygons
  that span neighbouring countries (e.g. `place=region`). If necessary, extend
  the SQL filters to exclude `place='region'` or other unwanted tags.
- **Custom schemas** – If you add custom tables, update the fallback list in
  `DatabaseManagerService._calculate_bounds` (async) and `_calculate_bounds_sync`
  (worker) to ensure bounds capture your data.

## Operational Tips

- If you import a completely new dataset outside the worker (e.g. manual psql),
  flush the cached bounds manually or re-run an import so the cache is refreshed.
- Use the cached envelope to drive downstream map rendering, tile seeding, or
  zoom-level heuristics. The values are in raw degrees and do not include padding.

For the full import flow, see `docs/import-pipeline.md`, and for how the map
consumes these values, refer to `docs/frontend.md`.
