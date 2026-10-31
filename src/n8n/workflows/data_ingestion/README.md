# Data Ingestion Workflows (n8n → DAPP)

Jager n8n workflows **do not** embed Python pipelines. They HTTP-trigger the DAPP control plane (`DATA_PIPELINE_URL` / `OLTP_PIPELINE_URL` → `http://dapp-api:8000`, header `X-API-Key`).

## MotherDuck (canonical analytics path)

See [`../olap/data_ingestion/`](../olap/data_ingestion/) — Buffer, Zernio, LinkedIn, Substack, Nager, CDB, plus newer Reddit / Meetup / Eurostat / WordPress / Yahoo / Notion / Manual MD syncs on DAPP `/run/ingest_*`.

## Still in this folder

| Source | Workflow | DAPP route |
|--------|----------|------------|
| Notion | [`data_ingestion_notion.json`](data_ingestion_notion.json) | `POST /run/oltp/ingest_notion` |
| Manual Notion | [`data_ingestion_manual.json`](data_ingestion_manual.json) | `POST /run/oltp/ingest_notion_manual` |
| Buffer / LinkedIn / Zernio / Substack / Reddit / Meetup / Eurostat / WordPress / Yahoo | matching `data_ingestion_*.json` | API → ops Postgres `s_*` (n8n or OLTP), then MotherDuck via `/run/ingest_*` |

Pipeline **code** lives only in the DAPP repo (`src/olap`, `src/oltp`). See [`../../dapp/README.md`](../../dapp/README.md).
