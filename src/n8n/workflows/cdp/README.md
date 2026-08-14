# CDP Workflows

This directory contains N8N workflows responsible for Customer Data Platform (CDP) lead processing, manual data ingestion, and weekly network review reporting.

---

## 1. CDP Lead Processing
* **File:** [cdp_lead_processing.json](cdp_lead_processing.json)
* **Description:** Fetches unprocessed LinkedIn connections from `s_linkedin.connections`, normalizes profile fields, and upserts them into `cdp.persons`.

---

## 2. CDP Manual Data Ingestion
* **File:** [cdp_manual_data_ingestion.json](cdp_manual_data_ingestion.json)
* **Description:** Periodically triggers the Python dlt manual data ingestion pipeline (`ingest_notion_manual.py`) via FastAPI (`POST /run/oltp/ingest_notion_manual`) to ingest databases and pages under Notion parent page `_manual_data_ingestion` into `s_manual` tables.

---

## 3. CDP Weekly Network Review
* **File:** [cdp_weekly_network_review.json](cdp_weekly_network_review.json)
* **Description:** Scheduled weekly workflow (Mondays at 09:00 AM) that queries CDP presentation models from `s_motherduck` (`sum_cdp_weekly_network_digest`, `cdp_leads`, `cdp_activities`, `cdp_persons`) and prompts Bella (Ollama Gemma 4) to generate a weekly network review summary and post it to Slack channel `#network`.
