#!/bin/sh
# Runs once on an empty data directory: Keycloak database and a read-only role for dev tooling.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v kc_pw="$KEYCLOAK_DB_PASSWORD" -v ro_pw="$FARM_RO_PASSWORD" <<'SQL'
CREATE ROLE keycloak LOGIN PASSWORD :'kc_pw';
CREATE DATABASE keycloak OWNER keycloak;
CREATE ROLE farm_ro LOGIN PASSWORD :'ro_pw';
GRANT CONNECT ON DATABASE farm TO farm_ro;
GRANT USAGE ON SCHEMA public TO farm_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE farm IN SCHEMA public GRANT SELECT ON TABLES TO farm_ro;
ALTER ROLE farm_ro SET default_transaction_read_only = on;
SQL
