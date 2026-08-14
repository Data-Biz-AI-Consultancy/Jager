#!/bin/sh

# Wait for PostgreSQL port to be ready
# Uses node (always available in n8n image) — /dev/tcp is bash-only and does not work in Alpine ash
echo "Waiting for PostgreSQL database to be ready..."
until node -e "
  const net = require('net');
  const s = net.createConnection(5432, 'db');
  s.on('connect', () => { s.destroy(); process.exit(0); });
  s.on('error',   () => { s.destroy(); process.exit(1); });
" 2>/dev/null; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Give PostgreSQL a brief moment to finish any lingering init operations
sleep 1

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

# Launch post-startup version repair in background.
# This runs AFTER n8n is fully up and has activated all workflows,
# catching any versionId drift that n8n's own activation phase introduces.
if [ -f /etc/n8n/repair-versions.sh ]; then
  sh /etc/n8n/repair-versions.sh &
fi

# Execute the default n8n entrypoint
echo "Starting N8N..."
exec /docker-entrypoint.sh "$@"
