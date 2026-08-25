#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create n8n database if not exists
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "jager" <<-EOSQL
	SELECT 'CREATE DATABASE n8n'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec
EOSQL

# Initialize OLTP database (jager database — raw staging & operational schemas)
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "jager" -f "$SCRIPT_DIR/sql/oltp_schema.sql"

# Seed reference data — skipped in CI (schema-only mode)
if [ "$CI" != "true" ]; then
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "jager" -f "$SCRIPT_DIR/sql/oltp_seeds.sql"
fi

