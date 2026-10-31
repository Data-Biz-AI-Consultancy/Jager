# MotherDuck Data Ingestion Workflow

Single n8n workflow that triggers all DAPP MotherDuck OLAP dlt ingest pipelines over HTTP.

## Auth & base URL

All HTTP Request nodes call DAPP with:

- **Base URL**: `{{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}`
- **Header**: `X-API-Key: {{ $env.DAPP_API_KEY }}`

Jager docker-compose injects `DATA_PIPELINE_URL` (default `http://dapp-api:8000`) and `DAPP_API_KEY` into the n8n service.

## Workflow

### [MotherDuck Data Ingestion](./motherduck_data_ingestion_jager.json)

* **Workflow ID**: `motherduck-data-ingestion-jager`
* **Trigger**: Daily `Schedule Trigger` (03:00), fans out in parallel to all 9 MotherDuck ingest endpoints
* **Endpoints**:
  * `POST /run/ingest_buffer`
  * `POST /run/ingest_zernio`
  * `POST /run/ingest_linkedin`
  * `POST /run/ingest_meetup`
  * `POST /run/ingest_reddit`
  * `POST /run/ingest_eurostat`
  * `POST /run/ingest_yahoo_finance_md`
  * `POST /run/ingest_manual`
  * `POST /run/ingest_nager`

## Not MotherDuck (do not add here)

* `/run/connectors/substack` and `/run/connectors/notion` — VectorDB connectors in DAPP, not MotherDuck dlt
* `/run/oltp/*` — OLTP → PostgreSQL pipelines
* Source→OLTP collectors under [`../../data_ingestion/`](../../data_ingestion/) (e.g. Buffer/Meetup collectors) are separate from these MotherDuck triggers

## Local Import & Setup

This workflow is automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow import from the workspace JSON file, ensure the containers are running and use:

```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json
```
