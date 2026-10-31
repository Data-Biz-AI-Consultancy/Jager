# MotherDuck Data Ingestion Workflows

n8n workflows that trigger DAPP MotherDuck OLAP dlt ingest pipelines and dbt over HTTP.

## Auth & base URL

HTTP Request nodes call DAPP with:

- **Base URL**: `{{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}`
- **Header**: `X-API-Key: {{ $env.DAPP_API_KEY }}`

Jager docker-compose injects `DATA_PIPELINE_URL` (default `http://dapp-api:8000`) and `DAPP_API_KEY` into the n8n service.

### Running DAPP alongside Jager (local)

n8n does **not** bundle `dapp-api`. Start DAPP on the same Docker network so `dapp-api` DNS works:

```bash
# 1) Shared bridge (once)
docker network create jager_network || true

# 2) Jager app stack (n8n on jager_network) — from Jager repo
#    set DAPP_API_KEY in Jager .env to the SAME value as DAPP .env, then:
docker compose --profile app up -d

# 3) DAPP stack — from DAPP repo root (joins jager_network; service name dapp-api)
docker compose up -d --build

# 4) Verify DNS from inside n8n
docker compose exec n8n wget -qO- http://dapp-api:8000/healthz
```

Keep the workflow default `http://dapp-api:8000` for Docker. Only override `DATA_PIPELINE_URL` (e.g. `http://localhost:8002`) if n8n runs on the host outside Docker. Do not remove `X-API-Key`.

## Workflows

### [MotherDuck Data Ingestion](./motherduck_data_ingestion_jager.json)

* **Workflow ID**: `motherduck-data-ingestion-jager`
* **Trigger**: Daily `Schedule Trigger` (03:00), fans out in parallel to MotherDuck ingest + dbt
* **Endpoints**:
  * `POST /run/ingest_buffer`
  * `POST /run/ingest_zernio`
  * `POST /run/ingest_linkedin`
  * `POST /run/ingest_meetup`
  * `POST /run/ingest_reddit`
  * `POST /run/ingest_eurostat`
  * `POST /run/ingest_yahoo_finance_md`
  * `POST /run/ingest_nager`
  * `POST /run/dbt_transform`

Omitted from this schedule: `ingest_manual`, `ingest_cdb` (not on the daily MotherDuck cron).

## Not MotherDuck (do not add here)

* `/run/connectors/substack` and `/run/connectors/notion` — VectorDB connectors; see [`../../ai_memory/dapp_connectors_notion_substack.json`](../../ai_memory/dapp_connectors_notion_substack.json)
* `/run/reverse_etl` — DAPP-only; no n8n trigger under this tree

## Local Import & Setup

These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow import from the workspace JSON file, ensure the containers are running and use:

```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json
```
