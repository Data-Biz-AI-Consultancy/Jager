# Use the official N8N image as the base
FROM n8nio/n8n:latest

USER root

# Copy custom entrypoint and workflows
COPY src/n8n/docker-entrypoint-custom.sh /docker-entrypoint-custom.sh
RUN chmod +x /docker-entrypoint-custom.sh

# Copy workflows to /etc/n8n/workflows
RUN mkdir -p /etc/n8n/workflows
COPY src/n8n/workflows/ /etc/n8n/workflows/
COPY src/n8n/credentials.json /etc/n8n/credentials.json
COPY src/n8n/bella.md /etc/n8n/bella.md
COPY src/n8n/giusy.md /etc/n8n/giusy.md
COPY src/n8n/import-workflows.js /etc/n8n/import-workflows.js
COPY scripts/migrate-db.js /etc/n8n/migrate-db.js


# Give node user ownership
RUN chown -R node:node /etc/n8n /docker-entrypoint-custom.sh

USER node

ENTRYPOINT ["tini", "--", "/docker-entrypoint-custom.sh"]

