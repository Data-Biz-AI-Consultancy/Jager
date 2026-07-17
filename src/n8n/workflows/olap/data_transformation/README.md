# OLAP Data Transformation Workflows

This directory contains n8n workflows designed to perform data transformations (modeling/marts calculations) within Motherduck.

## Workflows

### 1. [OLAP Data Transformation - dbt Core Motherduck](./olap_data_transformation_dbt_motherduck.json)
*   **Workflow ID**: `olap-dbt-transform-motherduck`
*   **Trigger**: Runs automatically every day via a `Schedule Trigger`.
*   **Purpose**: Triggers the `dbt build` run on the `data-pipeline` service to compile staging, intermediate, and marts models inside Motherduck.

## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_transformation/olap_data_transformation_dbt_motherduck.json
```

