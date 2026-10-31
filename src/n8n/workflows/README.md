# N8N Workflows Directory Structure

This directory contains the N8N workflow JSON definitions versioned in Git. Workflows are organized into subdirectories by domain and functional responsibility:

- **`cdb/`**: Client DataBase (CDB) orchestration and network review workflows (`cdb_weekly_network_review.json`).
- **`ai_memory/`**: Memory distillation, staging, embeddings, and thin DAPP VectorDB connector triggers (Notion / Substack).
- **`ai_summary/`**: AI content summary generation workflows.
- **`ai_retrieval/`**: AI content generation and retrieval workflows (LinkedIn / Substack publishing).
- **`olap/`**: MotherDuck ingest±dbt schedule and MotherDuck ops (`motherduck_ops.json`).
- **`auto_eda.json`**: Auto EDA orchestration at the workflows root.
