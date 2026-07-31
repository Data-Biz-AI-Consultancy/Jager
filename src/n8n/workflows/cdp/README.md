# CDP Workflows

This directory contains N8N workflows responsible for Customer Data Platform (CDP) lead processing and manual data ingestion.

---

## 1. CDP Lead Processing
* **File:** [cdp_lead_processing.json](cdp_lead_processing.json)
* **Description:** Fetches unprocessed LinkedIn connections from `s_linkedin.connections`, normalizes profile fields, and upserts them into canonical CDP person and client account tables (`cdp.persons`, `cdp.client_accounts`).

---

## 2. CDP Manual Data Ingestion
* **File:** [cdp_manual_data_ingestion.json](cdp_manual_data_ingestion.json)
* **Description:** Periodically triggers the Python dlt manual data ingestion pipeline (`ingest_notion_manual.py`) via FastAPI (`POST /run/oltp/ingest_notion_manual`) to ingest databases and pages under Notion parent page `_manual_data_ingestion` (`3ad6e98d4ef8808e90e5d12894842709`) into `s_manual` tables.
