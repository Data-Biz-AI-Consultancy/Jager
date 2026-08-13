#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	SELECT 'CREATE DATABASE n8n'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec
	SELECT 'CREATE DATABASE cdp'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'cdp')\gexec
EOSQL


# Initialize CDP database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cdp" -f "$SCRIPT_DIR/sql/cdp_schema.sql"

# Seed reference data — skipped in CI (schema-only mode)
if [ "$CI" != "true" ]; then
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cdp" -f "$SCRIPT_DIR/sql/cdp_seeds.sql"
fi


# Initialize OLTP database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$SCRIPT_DIR/sql/oltp_schema.sql"

# Seed reference data — skipped in CI (schema-only mode)
if [ "$CI" != "true" ]; then
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$SCRIPT_DIR/sql/oltp_seeds.sql"
fi
