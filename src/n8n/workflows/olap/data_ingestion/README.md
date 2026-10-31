# MotherDuck Data Ingestion Workflows

n8n workflows that trigger DAPP MotherDuck OLAP dlt ingest pipelines over HTTP.

## Auth & base URL (Jager schedule)

HTTP Request nodes in the Jager schedule call DAPP with:

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
#    If you added DAPP_API_KEY after n8n was already up:
#    docker compose --profile app up -d --force-recreate n8n

# 3) DAPP stack — from DAPP repo root (joins jager_network; service name dapp-api)
#    set SOURCE_DATABASE_URL=postgresql://jager:jager@db:5432/jager for OLAP extract
docker compose up -d --build

# 4) Verify DNS from inside n8n
docker compose exec n8n wget -qO- http://dapp-api:8000/healthz
```

Keep the workflow default `http://dapp-api:8000` for Docker. Only override `DATA_PIPELINE_URL` (e.g. `http://localhost:8002`) if n8n runs on the host outside Docker. Do not remove `X-API-Key`.

## Workflows

### [MotherDuck Data Ingestion](./motherduck_data_ingestion_jager.json)

* **Workflow ID**: `motherduck-data-ingestion-jager`
* **Trigger**: Daily `Schedule Trigger` (03:00), fans out in parallel to MotherDuck ingest endpoints
* **Endpoints**:
  * `POST /run/ingest_buffer`
  * `POST /run/ingest_zernio`
  * `POST /run/ingest_linkedin`
  * `POST /run/ingest_meetup`
  * `POST /run/ingest_reddit`
  * `POST /run/ingest_eurostat`
  * `POST /run/ingest_yahoo_finance_md`
  * `POST /run/ingest_manual`

### [MotherDuck Data Ingestion - Nager](./motherduck_data_ingestion_nager.json) (legacy / untouched this PR)

* **Workflow ID**: `motherduck-data-ingestion-nager`
* Kept as a **separate** workflow file, restored from `origin/main` and left unchanged for this PR (legacy URL/auth: `http://dapp:8000`, no `X-API-Key`)
* **Endpoint**: `POST /run/ingest_nager`

## Not MotherDuck (do not add here)

* `/run/connectors/substack` and `/run/connectors/notion` — VectorDB connectors in DAPP, not MotherDuck dlt
* `/run/oltp/*` — OLTP → PostgreSQL pipelines
* Source→OLTP collectors under [`../../data_ingestion/`](../../data_ingestion/) (e.g. Buffer/Meetup collectors) are separate from these MotherDuck triggers

## Local Import & Setup

These workflows are automatically imported into the local n8n instance upon running `docker compose up --build`.

To manually trigger workflow import from the workspace JSON file, ensure the containers are running and use:

```bash
docker compose exec n8n n8n import:workflow --input /etc/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json
```
