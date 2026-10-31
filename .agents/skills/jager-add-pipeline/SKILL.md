---
name: jager-add-pipeline
description: >-
  Use this skill when the user wants to add a new dlt ingestion pipeline.
  Pipeline code lives in the DAPP repo; Jager only triggers via n8n HTTP.
---

# Adding a dlt pipeline (DAPP-owned)

**Implementation home:** [Data-Biz-AI-Consultancy/DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP) under `src/olap/` (MotherDuck) or `src/oltp/` (ops Postgres).

Do **not** add Python pipelines under Jager — that tree was removed; implement in DAPP.
## In DAPP

1. Add `src/olap/ingest_<name>.py` (or `src/oltp/...`) using helpers from `common.utils` / `utils.db`.
2. Register in [`pipeline_runner.py`](https://github.com/Data-Biz-AI-Consultancy/DAPP/blob/main/src/api/pipeline_runner.py) and/or `src/api/routes/olap.py` / `oltp.py`.
3. Follow DAPP skill [dapp-motherduck-olap](https://github.com/Data-Biz-AI-Consultancy/DAPP/blob/main/.agents/skills/dapp-motherduck-olap/SKILL.md).

## In Jager (n8n only)

HTTP Request node:

- URL: `{{ $env.DATA_PIPELINE_URL }}/run/ingest_<name>` (or `/run/oltp/...`)
- Header: `X-API-Key: {{ $env.DAPP_API_KEY }}`
- Host default: `http://dapp-api:8000` via [`docker-compose.dapp.yml`](../../docker-compose.dapp.yml)
