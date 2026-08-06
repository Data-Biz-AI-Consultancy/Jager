#!/bin/sh
# repair-versions.sh — post-startup version alignment script
#
# Runs in the background after n8n is healthy and fixes the version drift
# that occurs when n8n activates workflows during its own startup and updates
# workflow_entity.versionId without syncing workflow_published_version.
#
# This is separate from the pre-startup repair in import-workflows.js because
# n8n itself may change versionId values during its activation phase.

N8N_HOST="${N8N_HOST:-localhost}"
N8N_PORT="${N8N_PORT:-5678}"
MAX_WAIT=120  # seconds to wait for n8n to be healthy

echo "[repair-versions] Waiting for n8n to be healthy at ${N8N_HOST}:${N8N_PORT}..."
waited=0
while ! nc -z "$N8N_HOST" "$N8N_PORT"; do
  sleep 2
  waited=$((waited + 2))
  if [ "$waited" -ge "$MAX_WAIT" ]; then
    echo "[repair-versions] Timed out waiting for n8n. Skipping post-startup repair."
    exit 0
  fi
done

# Give n8n a few extra seconds to finish its internal activation
sleep 5

echo "[repair-versions] n8n is up. Running post-startup version alignment..."
node /etc/n8n/post-startup-repair.js
echo "[repair-versions] Post-startup version alignment complete."
