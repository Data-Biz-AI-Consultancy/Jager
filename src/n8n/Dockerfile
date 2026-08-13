# Use official N8N image pinned to version 2.33.5
FROM n8nio/n8n:2.33.5

USER root

# Copy custom entrypoint and workflows
COPY src/n8n/docker-entrypoint-custom.sh /docker-entrypoint-custom.sh
RUN chmod +x /docker-entrypoint-custom.sh

# Copy workflows to /etc/n8n/workflows
RUN mkdir -p /etc/n8n/workflows
COPY src/n8n/workflows/ /etc/n8n/workflows/
COPY src/n8n/credentials.json /etc/n8n/credentials.json
COPY src/n8n/scripts/import-credentials.js /etc/n8n/import-credentials.js
COPY src/n8n/agents/ /etc/n8n/agents/
COPY src/n8n/scripts/import-workflows.js /etc/n8n/import-workflows.js
COPY src/n8n/scripts/post-startup-repair.js /etc/n8n/post-startup-repair.js
COPY src/n8n/scripts/repair-versions.sh /etc/n8n/repair-versions.sh
RUN chmod +x /etc/n8n/repair-versions.sh
COPY src/db/migrate-db.js /etc/n8n/migrate-db.js


# Give node user ownership
RUN chown -R node:node /etc/n8n /docker-entrypoint-custom.sh

USER node

ENTRYPOINT ["tini", "--", "/docker-entrypoint-custom.sh"]
