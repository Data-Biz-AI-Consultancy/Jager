#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Run application database migrations
if [ -f /etc/n8n/migrate-db.js ]; then
  echo "Running database schema migrations..."
  node /etc/n8n/migrate-db.js
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
