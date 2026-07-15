# Postgres & MotherDuck OLAP Workflows

This directory contains n8n workflows designed to manage and sync data ingestion to OLAP databases and perform transformations.

## Directory Structure

### 1. [Data Ingestion](./data_ingestion/README.md)
Contains workflows that ingest data into the Postgres OLAP and MotherDuck environments:
*   [Postgres OLAP Data Ingestion - Zernio](./data_ingestion/postgres_olap_data_ingestion_zernio.json)
*   [Postgres OLAP Data Ingestion - Buffer](./data_ingestion/postgres_olap_data_ingestion_buffer.json)
*   [Postgres OLAP Data Ingestion - LinkedIn](./data_ingestion/postgres_olap_data_ingestion_linkedin.json)
*   [MotherDuck Data Ingestion - Jager](./data_ingestion/motherduck_data_ingestion_jager.json)

### 2. [Data Transformation](./data_transformation/README.md)
Contains workflows that perform transformations within the OLAP database (`jager_olap`):
*   [OLAP Data Transformation - Content Marketing Performance](./data_transformation/olap_data_transformation_content_marketing_performance.json)

### 3. [ReverseETL](./reverse_etl/README.md)
Contains workflows that sync data back from OLAP databases (like MotherDuck) to OLTP databases (like PostgreSQL):
*   [OLAP ReverseETL - Motherduck to Postgres](./reverse_etl/olap_reverse_etl_motherduck_postgres.json)

### 4. MotherDuck Operations
*   [MotherDuck Operations](./motherduck_ops.json): Performs periodic configuration and sharing operations on MotherDuck (e.g. creating shares).


## Local Import & Setup
These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:
```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/postgres_olap_data_ingestion_zernio.json
```
