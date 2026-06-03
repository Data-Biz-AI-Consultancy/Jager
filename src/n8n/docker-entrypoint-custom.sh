#!/bin/sh

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Import credentials if they exist
if [ -f /etc/n8n/credentials.json ]; then
  echo "Importing N8N credentials..."
  n8n import:credentials --input /etc/n8n/credentials.json
fi

# Import workflows from workflows directory
if [ -d /etc/n8n/workflows ]; then
  for f in /etc/n8n/workflows/*.json; do
    if [ -f "$f" ]; then
      echo "Importing workflow: $f"
      n8n import:workflow --input "$f"
    fi
  done
fi

# Execute the default n8n entrypoint
echo "Starting N8N..."
exec /docker-entrypoint.sh
