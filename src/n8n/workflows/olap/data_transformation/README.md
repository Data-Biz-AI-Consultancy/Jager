# OLAP Data Transformation Workflows

This directory contains n8n workflows designed to perform data transformations (modeling/marts calculations) within the OLAP database (`jager_olap`).

## Workflows

### 1. [Content Marketing Performance](./content_marketing_performance.json)
*   **Workflow ID**: `content-marketing-performance`
*   **Trigger**: Runs automatically every 6 hours via a `Schedule Trigger`.
*   **Purpose**: Performs data transformations in the OLAP database (`jager_olap`) using a dbt-style layered modeling architecture (`staging`, `intermediate`, `marts` schemas) to compute post-level engagement metrics.

## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_transformation/content_marketing_performance.json
```
