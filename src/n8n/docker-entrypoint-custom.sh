#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Import workflows if the files exist
if [ -f /etc/n8n/reddit_workflow.json ]; then
  echo "Importing Reddit workflow..."
  n8n import:workflow --file /etc/n8n/reddit_workflow.json
fi

if [ -f /etc/n8n/workflow.json ]; then
  echo "Importing Instagram workflow..."
  n8n import:workflow --file /etc/n8n/workflow.json
fi

# Execute the default n8n entrypoint
echo "Starting N8N..."
exec /docker-entrypoint.sh
