# MotherDuck OLAP Workflows

This directory contains n8n workflows designed to manage and sync data ingestion to **MotherDuck** as the primary OLAP database.

## Workflows

### 1. [MotherDuck Data Ingestion - Jager](../src/n8n/workflows/data_ingestion/olap/motherduck_data_ingestion_jager.json)
*   **Workflow ID**: `motherduck-data-ingestion-jager`
*   **Trigger**: Runs automatically every 6 hours via a `Schedule Trigger`.
*   **Purpose**: Replicates processed data from PostgreSQL source tables into MotherDuck OLAP tables.
*   **Schemas Managed**:
    *   `s_zernio`: Contains LinkedIn post text, followers stats timeline, post analytics, account analytics, post timeline, and content decay analysis.
    *   `s_buffer`: Contains Buffer social posting channels and processed posts.
*   **Key Operations**:
    1.  **Schema & Table Initialization**: Automatically creates schemas (`s_zernio`, `s_buffer`) and target tables using `CREATE TABLE IF NOT EXISTS`.
    2.  **Data Replication**: Performs incremental updates and inserts from the application database utilizing `ON CONFLICT` clauses on primary keys to avoid duplicates.

---

### 2. [MotherDuck Operations](/src/n8n/workflows/data_ingestion/olap/motherduck_ops.json)
*   **Workflow ID**: `motherduck-ops`
*   **Trigger**: Runs automatically once every 24 hours via a `Schedule Trigger`.
*   **Purpose**: Performs periodic configuration and sharing operations on MotherDuck.
*   **Key Operations**:
    1.  **Create Motherduck Share**: Automatically creates and updates a shared instance of the staging database to grant discoverable access within the organization with auto-updating enabled:
        ```sql
        CREATE SHARE IF NOT EXISTS "{{ $env.MOTHERDUCK_DATABASE || 'staging' }}_share"
        FROM "{{ $env.MOTHERDUCK_DATABASE || 'staging' }}"
        (ACCESS ORGANIZATION, VISIBILITY DISCOVERABLE, UPDATE AUTOMATIC);
        ```

## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/data_ingestion/olap/motherduck_data_ingestion_jager.json
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/data_ingestion/olap/motherduck_ops.json
```

## References & Best Practices
For detailed recommendations, guidelines, and optimization patterns on using MotherDuck, refer to the [MotherDuck Best Practices Guide](../../../../../docs/motherduck_best_practices.md).

