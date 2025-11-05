#!/usr/bin/env bash
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
      CREATE ROLE app_user LOGIN PASSWORD 'app_password';
   END IF;
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_readonly') THEN
      CREATE ROLE app_readonly LOGIN PASSWORD 'app_readonly';
   END IF;
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'super_user') THEN
      CREATE ROLE super_user WITH LOGIN PASSWORD 'super_password' CREATEDB CREATEROLE;
   END IF;
END
\$\$;

GRANT CONNECT ON DATABASE osm_manager TO app_user, app_readonly, super_user;
GRANT ALL PRIVILEGES ON DATABASE osm_manager TO app_user;
GRANT USAGE ON SCHEMA public TO app_user, app_readonly, super_user;
GRANT CREATE ON SCHEMA public TO app_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
GRANT ALL ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO app_user;
EOSQL
