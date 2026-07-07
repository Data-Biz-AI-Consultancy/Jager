# Data Ingestion Workflows

This directory contains N8N workflows responsible for ingesting external data (Substack, LinkedIn, Eurostat, Yahoo Finance, etc.) into the Jager PostgreSQL database.

---

## 1. Substack Ingestion
* **File:** [data_ingestion_substack.json](file:///Users/jimmypang/AntigravityProjects/Jager/src/n8n/workflows/data_ingestion/data_ingestion_substack.json)
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
