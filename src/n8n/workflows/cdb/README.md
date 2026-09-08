# CDB Workflows

This directory contains n8n workflows responsible for Client DataBase (CDB) lead processing, identity resolution orchestration, and weekly network review reporting.

For full architectural details, database schemas, and API documentation of the CDB microservice, see the [CDB Documentation](../../../docs/cdb/Implementation_plan.md) and [Jager Integration Guide](../../../docs/cdb/JAGER_INTEGRATION.md).

---

## 1. CDB Lead Processing (Migrated to CDB Native Connectors)
* **Status:** Deprecated & Migrated directly into the [CDB repository](../../../../cdb)
* **Description:** Formerly a periodically scheduled workflow (runs every 6 hours) that pulled LinkedIn data and Notion meeting notes from Postgres and POSTed to CDB. Data ingestion for all direct channels (**LinkedIn messages & connections**, **Notion meeting notes**) has now migrated into CDB's native background connectors (`cdb.services.connectors.linkedin` and `cdb.services.connectors.notion`) with automated Celery Beat scheduling.

---

## 2. CDB Weekly Network Review
* **File:** [cdb_weekly_network_review.json](cdb_weekly_network_review.json)
* **Description:** Scheduled weekly workflow (Mondays at 09:00 AM) that queries CDB presentation models from `s_motherduck` (`sum_cdp_weekly_network_digest`, `cdp_leads`, `cdp_activities`, `cdp_persons`), prompts the LLM agent to generate a weekly network review summary, and posts the report to Slack.
