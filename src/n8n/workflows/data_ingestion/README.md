# Data Ingestion Workflows (n8n → DAPP)

Jager n8n workflows **do not** embed Python pipelines. They HTTP-trigger the DAPP control plane (`DATA_PIPELINE_URL` / `OLTP_PIPELINE_URL` → `http://dapp-api:8000`, header `X-API-Key`).

## MotherDuck (canonical analytics path)

See [`../olap/data_ingestion/`](../olap/data_ingestion/) — Buffer, Zernio, LinkedIn, Substack, Nager, CDB, Reddit, Meetup, Eurostat, WordPress, Yahoo, Notion MD syncs on DAPP `POST /run/ingest_*`.

## OLTP (Notion only)

| Source | Workflow | DAPP route |
|--------|----------|------------|
| Notion | [`data_ingestion_notion.json`](data_ingestion_notion.json) | `POST /run/oltp/ingest_notion` |
| Manual Notion | [`data_ingestion_manual.json`](data_ingestion_manual.json) | `POST /run/oltp/ingest_notion_manual` |

WordPress / Yahoo / Eurostat FX thin OLTP triggers were removed — use OLAP MotherDuck ingest instead.

Pipeline **code** lives only in the [DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP) repo (`src/olap`, `src/oltp`).
