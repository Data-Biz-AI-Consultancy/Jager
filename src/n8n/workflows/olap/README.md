# MotherDuck OLAP Workflows

n8n workflows that trigger DAPP MotherDuck ingestion, dbt transforms, and reverse ETL.

## Caller contract

HTTP Request nodes use:

* **Base URL**: `{{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}`
* **Auth**: `X-API-Key: {{ $env.DAPP_API_KEY }}`

## Directory Structure

### 1. [Data Ingestion](./data_ingestion/README.md)

Single workflow that fans out to all DAPP MotherDuck `/run/ingest_*` endpoints:

* [MotherDuck Data Ingestion](./data_ingestion/motherduck_data_ingestion_jager.json) (`buffer`, `zernio`, `linkedin`, `meetup`, `reddit`, `eurostat`, `yahoo_finance_md`, `manual`, `nager`)

### 2. [Data Transformation](./data_transformation/README.md)

Contains workflows that perform transformations in MotherDuck using dbt Core:

* [OLAP Data Transformation - dbt Core Motherduck](./data_transformation/olap_data_transformation_dbt_motherduck.json)

### 3. [ReverseETL](./reverse_etl/README.md)

Contains workflows that sync data back from MotherDuck to PostgreSQL OLTP:

* [OLAP ReverseETL - Motherduck to Postgres](./reverse_etl/olap_reverse_etl_motherduck_postgres.json)

### 4. MotherDuck Operations

* [MotherDuck Operations](./motherduck_ops.json): Performs periodic configuration and sharing operations on MotherDuck (e.g. creating shares). Not an HTTP ingest trigger.


## Local Import & Setup

These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:

```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json
```
