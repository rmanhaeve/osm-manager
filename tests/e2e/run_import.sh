#!/usr/bin/env bash
set -euo pipefail

# Example e2e workflow launching the stack and triggering an import using the sample stub PBF.
# Requires docker compose and osm2pgsql in the container.

SCRIPT_DIR=$(cd -- "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
PROJECT_ROOT="$SCRIPT_DIR/../.."

pushd "$PROJECT_ROOT" >/dev/null

docker compose up -d postgres redis api worker beat frontend

# wait for api
until curl -sSf http://localhost:8000/health >/dev/null; do
  echo "Waiting for API..."
  sleep 2
done

cp tests/data/sample.osm.pbf data/pbf/sample.osm.pbf

curl -sSf -X POST http://localhost:8000/databases \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: change-me" \
  -d '{"name": "test", "display_name": "Test DB"}'

curl -sSf -X POST http://localhost:8000/imports \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: change-me" \
  -d '{"target_db": "test", "mode": "create", "pbf_path": "/data/pbf/sample.osm.pbf"}'

popd >/dev/null
