# CDB Workflows

This directory contains n8n workflows responsible for Client DataBase (CDB) lead processing, identity resolution orchestration, and weekly network review reporting.

For full architectural details, database schemas, and API documentation of the CDB microservice, see the [CDB Documentation](../../../docs/cdb/Implementation_plan.md) and [Jager Integration Guide](../../../docs/cdb/JAGER_INTEGRATION.md).

---

## 1. CDB Lead Processing
* **File:** [cdb_lead_processing.json](cdb_lead_processing.json)
* **Description:** Periodically scheduled workflow (runs every 6 hours) that fetches unprocessed raw data across all 4 operational sources (**LinkedIn connections**, **LinkedIn messages**, **Notion meeting notes**, and **Notion manual data from `s_manual`**) in parallel from Jager's Postgres database, aggregates them into a single batch payload, and posts to CDB:
  * `POST /api/v1/ingest/batch` (`CDB_SERVICE_URL` with `X-API-Key` auth) - Ingests all pending sources in a single HTTP request, triggers incremental Entity Resolution, and removes legacy segment evaluation steps.

---

## 2. CDB Weekly Network Review
* **File:** [cdb_weekly_network_review.json](cdb_weekly_network_review.json)
* **Description:** Scheduled weekly workflow (Mondays at 09:00 AM) that queries CDB presentation models from `s_motherduck` (`sum_cdp_weekly_network_digest`, `cdp_leads`, `cdp_activities`, `cdp_persons`), prompts the LLM agent to generate a weekly network review summary, and posts the report to Slack.
