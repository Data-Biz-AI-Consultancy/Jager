# CDB Workflows

This directory contains n8n workflows responsible for Client DataBase (CDB) lead processing, identity resolution orchestration, and weekly network review reporting.

For full architectural details, database schemas, and API documentation of the CDB microservice, see the [CDB Documentation](../../../docs/cdb/Implementation_plan.md) and [Jager Integration Guide](../../../docs/cdb/JAGER_INTEGRATION.md).

---

## 1. CDB Lead Processing
* **File:** [cdb_lead_processing.json](cdb_lead_processing.json)
* **Description:** Periodically scheduled workflow (runs every 6 hours) that orchestrates entity resolution and lead intake by calling HTTP endpoints on the CDB FastAPI service (`CDB_SERVICE_URL` with `X-API-Key` auth):
  * `POST /api/v1/ingest/linkedin-connections` - Ingests LinkedIn connections into CDB.
  * `POST /api/v1/ingest/manual` - Ingests manual data into CDB.
  * `POST /api/v1/ingest/linkedin-messages` - Ingests LinkedIn messages into CDB.
  * `POST /api/v1/ingest/notion-meeting-notes` - Ingests Notion meeting notes into CDB.
  * `POST /process/evaluate_segments` - Refreshes dynamic person and lead segment assignments (legacy/transitional).

---

## 2. CDB Weekly Network Review
* **File:** [cdb_weekly_network_review.json](cdb_weekly_network_review.json)
* **Description:** Scheduled weekly workflow (Mondays at 09:00 AM) that queries CDB presentation models from `s_motherduck` (`sum_cdp_weekly_network_digest`, `cdp_leads`, `cdp_activities`, `cdp_persons`), prompts the LLM agent to generate a weekly network review summary, and posts the report to Slack.
