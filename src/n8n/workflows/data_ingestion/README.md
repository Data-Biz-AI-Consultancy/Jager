# Data Ingestion Workflows

This directory contains n8n workflows responsible for ingesting external data sources into PostgreSQL schemas (`s_*`).

---

## 📋 Available Ingestion Workflows

| Source | Workflow JSON | Target Schema | Description |
|--------|---------------|---------------|-------------|
| **Substack** | [`data_ingestion_substack.json`](data_ingestion_substack.json) | `s_substack.posts` | Fetches posts, metrics, comments, and reactions from monitored feeds |
| **Zernio (LinkedIn)** | [`data_ingestion_zernio.json`](data_ingestion_zernio.json) | `s_zernio` | Pulls LinkedIn company page post metrics and aggregate analytics via Zernio |
| **Buffer** | [`data_ingestion_buffer.json`](data_ingestion_buffer.json) | `s_buffer` | Fetches organization channels and post metrics with cursor-based pagination |
| **Notion (Pages & Notes)** | [`data_ingestion_notion.json`](data_ingestion_notion.json) | `s_notion.pages`, `s_notion.meeting_notes` | Ingests workspace knowledge pages and structured meeting notes |
| **Manual Files (Notion)** | [`data_ingestion_manual.json`](data_ingestion_manual.json) | `s_manual.*` | Triggers Python dlt pipeline (`POST /run/oltp/ingest_notion_manual`) for CSV/XLSX exports |
