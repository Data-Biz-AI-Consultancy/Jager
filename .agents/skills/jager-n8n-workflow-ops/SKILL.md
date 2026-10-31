---
name: jager-n8n-workflow-ops
description: >-
  Use this skill when developing, testing, or updating n8n workflows in Jager, including
  content scheduling & dual-track publishing (LinkedIn personal vs Data Biz Zernio),
  AI agent persona definitions, prompt templates, and syncing workflow JSON files.
---

# Jager n8n Workflows & Automation Architecture

Jager uses **n8n** as its primary workflow orchestrator, scheduling jobs, running AI prompts, and calling external APIs and internal microservices.

---

## 1. Workflow Domains & Directory Structure

All workflow JSON files are tracked under [`src/n8n/workflows/`](../../src/n8n/workflows/):

| Domain | Directory | Purpose |
|--------|-----------|---------|
| **Content Publishing** | `ai_retrieval/` | Content scheduling & dual-track publishing to LinkedIn |
| **AI Memory** | `ai_memory/` | Staging, fact extraction, episodic memory, and thin DAPP VectorDB connectors |
| **OLAP & dlt Sync** | `olap/` | Consolidated MotherDuck ingest±dbt schedule + MotherDuck ops |
| **CDB Integration** | `cdb/` | REST API webhook sync to CDB (`CDB_SERVICE_URL`) |

Obsolete `data_ingestion/` (apps→Postgres collectors) and `ml/` workflow trees were removed; ingestion lives in DAPP and is triggered via thin HTTP schedules under `olap/` / `ai_memory/`.

---

## 2. Dual-Track LinkedIn Publishing Architecture (`ai_retrieval/`)

Posts stored in `t_content_generation.linkedin_posts` are dispatched via two distinct paths:

```
Scheduler Cron ──► Calculate Slots (skip weekends) ──► Mark Scheduled
                                                            │
Publisher (every 15m) ──► Query Due (scheduled_at <= NOW()) ┴────────┐
                                                                      ▼
                       ┌──────────────────────────────┬──────────────────────────────┐
                       ▼                                                             ▼
             Track A: Individual Channel                                  Track B: Data Biz Channel
         (Native LinkedIn OAuth2 API)                                        (Zernio Post API)
                       │                                                             │
                       ▼                                                             ▼
           POST api.linkedin.com/rest/posts                              POST zernio.com/api/v1/posts
                       │                                                             │
                       ▼                                                             ▼
             Save external_post_id                                         Save external_post_id
```

### Table Schema: `t_content_generation.linkedin_posts`
- `channel`: `'individual'` or `'databiz'`
- `is_approved`, `is_scheduled`, `is_published`: Booleans controlling stage progression
- `scheduled_at`: Target publication timestamp

---

## 3. AI Persona & Prompt File Conventions

- **Agent Persona Markdown Files**: Stored in `src/n8n/agents/` (one file per agent). Must define `Role`, `LLM`, and `Personality & Grounding`.
- **Language & Formatting**:
  - Must communicate **entirely in English** (at most a single Italian greeting/sign-off).
  - Use real Unicode emojis (💡, 📊), never text codes (`:sparkles:`).
  - Slack links must use `<url|Anchor Text>` syntax.
- **Standalone Prompts**: Stored in `prompts/`. Must use `{{VARIABLE_NAME}}` placeholders and explicitly state output formats (e.g. "Output only the raw JSON block").

---

## 4. Environment & Secrets Injection

- In local development, environment variables are loaded via `.env` and `docker-compose.yml`.
- Never commit secrets to workflow JSON files. Always reference n8n expressions `{{ $env.VARIABLE_NAME }}` or credentials entities.

---

## 5. MotherDuck OLAP Triggers → DAPP

Workflows under [`src/n8n/workflows/olap/data_ingestion/`](../../src/n8n/workflows/olap/data_ingestion/) trigger **DAPP** MotherDuck dlt pipelines (not an in-repo `dapp` service):

- **Base URL**: `{{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}`
- **Auth**: every HTTP Request node in the Jager schedule sends `X-API-Key: {{ $env.DAPP_API_KEY }}`
- **Coverage**: [`motherduck_data_ingestion_jager.json`](../../src/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json) fans out in parallel to DAPP `POST /run/ingest_*` (`buffer`, `zernio`, `linkedin`, `meetup`, `reddit`, `eurostat`, `yahoo_finance_md`, `nager`) plus `POST /run/dbt_transform`. Omits `ingest_manual` / `ingest_cdb` from the daily schedule.
- **Ops**: keep [`motherduck_ops.json`](../../src/n8n/workflows/olap/motherduck_ops.json) for share/DDL; not an ingest trigger.
- **Reverse ETL**: DAPP still exposes `POST /run/reverse_etl`; there is no n8n reverse-ETL trigger under `src/n8n/workflows/olap/`
- **VectorDB connectors**: [`dapp_connectors_notion_substack.json`](../../src/n8n/workflows/ai_memory/dapp_connectors_notion_substack.json) POSTs `/run/connectors/notion?mode=vectordb` and `/run/connectors/substack` with the same DAPP auth — do not put these in MotherDuck workflows
