# OLAP Data Transformation (dbt)

Separate from MotherDuck **ingest**. This workflow only triggers DAPP dbt against MotherDuck.

## Auth & base URL

- **Base URL**: `{{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}`
- **Header**: `X-API-Key: {{ $env.DAPP_API_KEY }}`

## Workflow

### [OLAP Data Transformation - dbt Core Motherduck](./olap_data_transformation_dbt_motherduck.json)

* **Workflow ID**: `olap-dbt-transform-motherduck`
* **Trigger**: Daily schedule (05:00 by default; inactive until enabled)
* **Endpoint**: `POST /run/dbt_transform` (alias of `/run/dbt_build`)

Run **after** ingest has loaded fresh MotherDuck data (see [MotherDuck Data Ingestion](../data_ingestion/motherduck_data_ingestion_jager.json)).

## Local import

```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_transformation/olap_data_transformation_dbt_motherduck.json
```
