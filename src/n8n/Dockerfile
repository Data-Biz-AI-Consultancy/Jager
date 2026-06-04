# Use the official N8N image as the base
FROM n8nio/n8n:latest

USER root

# Copy custom entrypoint and workflows
COPY docker-entrypoint-custom.sh /docker-entrypoint-custom.sh
RUN chmod +x /docker-entrypoint-custom.sh

# Copy workflows to /etc/n8n/workflows
RUN mkdir -p /etc/n8n/workflows
COPY workflows/ /etc/n8n/workflows/
COPY credentials.json /etc/n8n/credentials.json
COPY bella.md /etc/n8n/bella.md


# Give node user ownership
RUN chown -R node:node /etc/n8n /docker-entrypoint-custom.sh

USER node

ENTRYPOINT ["tini", "--", "/docker-entrypoint-custom.sh"]

