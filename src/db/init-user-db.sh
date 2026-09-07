#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create n8n database if not exists
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "jager" <<-EOSQL
	SELECT 'CREATE DATABASE n8n'
	WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n')\gexec
EOSQL

# Initialize OLTP database (jager database — raw staging & operational schemas)
for f in "$SCRIPT_DIR"/sql/schema/*.sql; do
	[ -f "$f" ] || continue
	echo "Applying schema file: $f"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "jager" -f "$f"
done

# Seed reference data — skipped in CI (schema-only mode)
if [ "$CI" != "true" ]; then
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "jager" -f "$SCRIPT_DIR/sql/oltp_seeds.sql"
fi

