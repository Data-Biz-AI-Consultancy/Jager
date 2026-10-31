# MotherDuck OLAP Workflows

n8n workflows that trigger DAPP MotherDuck ingestion and dbt transforms.

## Caller contract

HTTP Request nodes use:

* **Base URL**: `{{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}`
* **Auth**: `X-API-Key: {{ $env.DAPP_API_KEY }}`

## Directory Structure

### 1. [Data Ingestion](./data_ingestion/README.md)

* [MotherDuck Data Ingestion](./data_ingestion/motherduck_data_ingestion_jager.json) — single daily schedule fans out in parallel to DAPP `/run/ingest_*` (`buffer`, `zernio`, `linkedin`, `meetup`, `reddit`, `eurostat`, `yahoo_finance_md`, `nager`) plus `/run/dbt_transform`

Standalone dbt and per-source MotherDuck schedules were folded into this workflow.

### 2. MotherDuck Operations

* [MotherDuck Operations](./motherduck_ops.json): Periodic configuration and sharing operations on MotherDuck (e.g. creating shares). Not an HTTP ingest trigger.

Reverse ETL is exposed as DAPP `POST /run/reverse_etl` only; there is no n8n reverse-ETL trigger workflow under this tree.

VectorDB connectors (Notion / Substack) live under [`../ai_memory/dapp_connectors_notion_substack.json`](../ai_memory/dapp_connectors_notion_substack.json), not here.

## Local Import & Setup

These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow imports from the workspace JSON files, ensure the containers are running and use:

```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json
```
