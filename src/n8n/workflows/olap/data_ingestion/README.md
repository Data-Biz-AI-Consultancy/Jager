# MotherDuck Data Ingestion Workflows

This directory contains n8n workflows designed to manage and sync data ingestion from the OLTP PostgreSQL database (`jager`) to MotherDuck.

## Workflows

### 1. [MotherDuck Data Ingestion - Jager](./motherduck_data_ingestion_jager.json)
*   **Workflow ID**: `motherduck-data-ingestion-jager`
*   **Trigger**: Runs automatically every day via a `Schedule Trigger`.
*   **Purpose**: Replicates processed data from PostgreSQL source tables into MotherDuck OLAP tables (cloud-based) using DLT ingestion pipelines (Buffer, Zernio, LinkedIn, Substack).

### 2. [MotherDuck Data Ingestion - Nager](./motherduck_data_ingestion_nager.json)
*   **Workflow ID**: `motherduck-data-ingestion-nager`
*   **Trigger**: Runs automatically every day via a `Schedule Trigger`.
*   **Purpose**: Replicates public holidays data from PostgreSQL source tables into MotherDuck OLAP tables using the DLT Nager ingestion pipeline.

## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json
```

