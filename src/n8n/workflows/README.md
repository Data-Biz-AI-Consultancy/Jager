# N8N Workflows Directory Structure

This directory contains the N8N workflow JSON definitions versioned in Git. Workflows are organized into subdirectories by domain and functional responsibility:

- **`cdb/`**: Client DataBase (CDB) processing, entity resolution, and network review workflows (`cdb_lead_processing.json`, `cdb_weekly_network_review.json`).
- **`cdp/`**: Customer Data Platform (CDP legacy) processing and entity resolution workflows (`cdp_lead_processing.json`, `cdp_weekly_network_review.json`).
- **`data_ingestion/`**: Operational data source ingestion workflows (Buffer, Eurostat, LinkedIn raw, Meetup, Notion, Reddit, Substack, WordPress, Yahoo Finance, Zernio).
- **`ai_memory/`**: Memory distillation, staging, and vector embeddings workflows.
- **`ai_summary/`**: AI content summary generation workflows.
- **`ai_retrieval/`**: AI content generation and retrieval workflows.
- **`ml/`**: Machine learning training and prediction workflows.
- **`olap/`**: OLAP transformation and reverse ETL workflows.
