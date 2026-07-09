# Postgres & MotherDuck OLAP Workflows

This directory contains n8n workflows designed to manage and sync data ingestion to OLAP databases.

## Workflows

### 1. [Postgres OLAP Data Ingestion - Jager](./postgres_olap_data_ingestion_jager.json)
*   **Workflow ID**: `postgres-olap-data-ingestion-jager`
*   **Trigger**: Runs automatically every 6 hours via a `Schedule Trigger`.
*   **Purpose**: Replicates processed data from the PostgreSQL `jager` (OLTP) database into the `jager_olap` (OLAP) database on the same instance.
*   **Schemas Managed**:
    *   `s_zernio`: Contains LinkedIn post text, followers stats timeline, post analytics, account analytics, post timeline, and content decay analysis.
    *   `s_buffer`: Contains Buffer social posting channels and processed posts.
*   **Key Operations**:
    1.  **Schema & Table Initialization**: Automatically creates schemas (`s_zernio`, `s_buffer`) and target tables using `CREATE TABLE IF NOT EXISTS`.
    2.  **Data Replication**: Performs incremental updates and inserts from the application database utilizing `ON CONFLICT` clauses on primary keys to avoid duplicates.

---

### 2. [MotherDuck Data Ingestion - Jager](./motherduck_data_ingestion_jager.json)
*   **Workflow ID**: `motherduck-data-ingestion-jager`
*   **Purpose**: Replicates processed data from PostgreSQL source tables into MotherDuck OLAP tables (cloud-based).

---

### 3. [MotherDuck Operations](./motherduck_ops.json)
*   **Workflow ID**: `motherduck-ops`
*   **Purpose**: Performs periodic configuration and sharing operations on MotherDuck (e.g. creating shares).

## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/data_ingestion/olap/postgres_olap_data_ingestion_jager.json
```

