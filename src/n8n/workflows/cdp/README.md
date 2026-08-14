# CDP Workflows

This directory contains n8n workflows responsible for Customer Data Platform (CDP) lead processing, identity resolution orchestration, and weekly network review reporting.

For full architectural details, database schemas, and processor logic of the underlying CDP microservice, see the [CDP Service Documentation](../../../cdp/README.md).

---

## 1. CDP Lead Processing
* **File:** [cdp_lead_processing.json](cdp_lead_processing.json)
* **Description:** Periodically scheduled workflow (runs every 6 hours) that orchestrates entity resolution and lead intake by calling HTTP endpoints on the CDP FastAPI service (`CDP_SERVICE_URL`):
  * `POST /process/linkedin_connections` - Ingests LinkedIn connections into `cdp.persons_linkedins` and `cdp.companies`.
  * `POST /process/manual_data` - Ingests manual data into `cdp.persons_manual_substack` and `cdp.leads_manual`.
  * `POST /process/linkedin_messages` - Ingests LinkedIn messages into `cdp.leads_linkedin`.
  * `POST /process/notion_meeting_notes` - Ingests Notion meeting notes into `cdp.activities_notion_meeting_notes`.
  * `POST /process/evaluate_segments` - Refreshes dynamic person and lead segment assignments.

---

## 2. CDP Weekly Network Review
* **File:** [cdp_weekly_network_review.json](cdp_weekly_network_review.json)
* **Description:** Scheduled weekly workflow (Mondays at 09:00 AM) that queries CDP presentation models from `s_motherduck` (`sum_cdp_weekly_network_digest`, `cdp_leads`, `cdp_activities`, `cdp_persons`), prompts the LLM agent to generate a weekly network review summary, and posts the report to Slack.
