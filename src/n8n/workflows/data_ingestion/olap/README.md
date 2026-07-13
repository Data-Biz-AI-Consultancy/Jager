# Postgres & MotherDuck OLAP Workflows

This directory contains n8n workflows designed to manage and sync data ingestion to OLAP databases.

## Workflows

### 1. [Postgres OLAP Data Ingestion - Zernio](./postgres_olap_data_ingestion_zernio.json)
*   **Workflow ID**: `postgres-olap-ingestion-zernio`
*   **Trigger**: Runs automatically every 6 hours via a `Schedule Trigger`.
*   **Purpose**: Replicates Zernio LinkedIn Analytics data (`s_zernio` schema) from the PostgreSQL `jager` (OLTP) database into the `jager_olap` (OLAP) database.

### 2. [Postgres OLAP Data Ingestion - Buffer](./postgres_olap_data_ingestion_buffer.json)
*   **Workflow ID**: `postgres-olap-ingestion-buffer`
*   **Trigger**: Runs automatically every 6 hours via a `Schedule Trigger`.
*   **Purpose**: Replicates Buffer analytics data (`s_buffer` schema) from the PostgreSQL `jager` (OLTP) database into the `jager_olap` (OLAP) database.

### 3. [Postgres OLAP Data Ingestion - LinkedIn](./postgres_olap_data_ingestion_linkedin.json)
*   **Workflow ID**: `postgres-olap-ingestion-linkedin`
*   **Trigger**: Runs automatically every 6 hours via a `Schedule Trigger`.
*   **Purpose**: Replicates LinkedIn member portability data (`s_linkedin` schema) from the PostgreSQL `jager` (OLTP) database into the `jager_olap` (OLAP) database.

---

### 4. [MotherDuck Data Ingestion - Jager](./motherduck_data_ingestion_jager.json)
*   **Workflow ID**: `motherduck-data-ingestion-jager`
*   **Purpose**: Replicates processed data from PostgreSQL source tables into MotherDuck OLAP tables (cloud-based).

---

### 5. [MotherDuck Operations](./motherduck_ops.json)
*   **Workflow ID**: `motherduck-ops`
*   **Purpose**: Performs periodic configuration and sharing operations on MotherDuck (e.g. creating shares).

## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/data_ingestion/olap/postgres_olap_data_ingestion_zernio.json
```

