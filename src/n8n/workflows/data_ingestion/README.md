# Data Ingestion Workflows

This directory contains N8N workflows responsible for ingesting external data (Substack, LinkedIn, Eurostat, Yahoo Finance, etc.) into the Jager PostgreSQL database.

---

## 1. Substack Ingestion
* **File:** [data_ingestion_substack.json](../src/n8n/workflows/data_ingestion/data_ingestion_substack.json)
* **Description:** Fetches posts from monitored Substack feeds, retrieves rich metadata and post analytics (comments, reactions, restacks) via the unofficial Substack API, and upserts them into `s_substack.posts`.
* **API Reference:** [Substack Explorer API Docs](https://www.substackexplorer.com/api-docs)

---

## 2. Zernio LinkedIn Analytics Ingestion
* **File:** [data_ingestion_zernio.json](../src/n8n/workflows/data_ingestion/data_ingestion_zernio.json)
* **Description:** Periodically connects to Zernio to pull LinkedIn profile aggregate metrics and detailed post-level analytics (impressions, clicks, reactions, comments, shares, saves, sends), saving them to the `s_zernio` schema.
* **API Reference:** [Zernio Analytics API Docs](https://docs.zernio.com/analytics/get-analytics)
* **Context & Workaround Rationale:**
  * **Why Zernio?** LinkedIn natively requires formal, legal registration of a company to approve access to their **Community Management API** (necessary for organic post-level analytics). For personal analytics and lightweight developer integrations, this administrative process represents major overkill.
  * **The Solution:** We leverage Zernio (a unified 3rd party social platform partner of LinkedIn) as a workaround to query analytics data through simple API keys without managing individual OAuth approval processes or legal entities.

---

## 3. Buffer Ingestion
* **File:** [data_ingestion_buffer.json](../src/n8n/workflows/data_ingestion/data_ingestion_buffer.json)
* **Description:** Periodically fetches organizations, channels, and post analytics from Buffer, updating the `s_buffer` schema.
* **API Reference:** [Buffer GraphQL API Reference](https://developers.buffer.com/reference.html#field-posts)
* **Looping & Pagination Design:**
  * **GraphQL Schema Design Constraint:** The Buffer API is designed such that posts are nested under individual channels (`Channel.posts`). There is no global endpoint to query all posts across all channels at once.
  * **Implementation:** Consequently, the workflow must loop through each retrieved channel one-by-one, initiating pagination using a cursor-based approach for each channel to retrieve and ingest its associated posts.

---

## 4. Manual Data Ingestion (Notion)
* **File:** [data_ingestion_manual.json](data_ingestion_manual.json)
* **Schedule:** Daily at **07:00 UTC** (also supports on-demand via Manual Trigger)
* **Description:** Triggers the Python dlt pipeline (`ingest_notion_manual.py`) via the data pipeline service (`POST /run/oltp/ingest_notion_manual`). The pipeline reads any database or page under the Notion parent page `_manual_data_ingestion` (ID: `3ad6e98d4ef8808e90e5d12894842709`) and ingests them into `s_manual.*` tables using the naming convention `notion__<child_page_prefix>_<entity_name>`.
* **Downstream:** The `CDP - Manual Data Ingestion` workflow (in `cdp/`) depends on this and runs at 07:30 UTC to process `s_manual` rows into `cdp.*` entities.

### Current Manual Export Sources

| Source | Notion Child Page | Target Table Pattern |
|---|---|---|
| Substack subscriber export (CSV) | `substack` | `s_manual.notion__substack_<export_name>` |

> Additional manual export sources (e.g. LinkedIn exports) will be added under the same Notion parent page and picked up automatically by this pipeline.

