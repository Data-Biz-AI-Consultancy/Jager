#!/bin/sh

# Wait for PostgreSQL to be ready (port open)
echo "Waiting for PostgreSQL database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL port is open. Waiting for the jager database to accept connections..."

# Wait until the jager DB actually accepts queries (not just port open)
until node -e "
const pgPath = require.resolve('pg', { paths: ['/usr/local/lib/node_modules/n8n'] });
const { Client } = require(pgPath);
const c = new Client({ host: 'db', port: 5432, database: 'jager', user: 'jager', password: 'jager' });
c.connect().then(() => { c.end(); process.exit(0); }).catch(() => process.exit(1));
" 2>/dev/null; do
  echo "Jager database not ready yet, retrying in 2s..."
  sleep 2
done
echo "Jager database is ready!"

# Run application database migrations — fail hard if this errors
if [ -f /etc/n8n/migrate-db.js ]; then
  echo "Running database schema migrations..."
  node /etc/n8n/migrate-db.js
  if [ $? -ne 0 ]; then
    echo "ERROR: Database migration failed! Aborting container startup."
    exit 1
  fi
  echo "Database schema migrations completed successfully."
fi

# Import credentials if they exist
if [ -f /etc/n8n/import-credentials.js ]; then
  echo "Checking and importing new credentials..."
  node /etc/n8n/import-credentials.js
fi

# Import workflows using comparison script to preserve active state of unchanged workflows
if [ -f /etc/n8n/import-workflows.js ]; then
  echo "Checking and importing workflows..."
  node /etc/n8n/import-workflows.js
fi

# Execute the default n8n entrypoint
echo "Starting N8N..."
exec /docker-entrypoint.sh "$@"
