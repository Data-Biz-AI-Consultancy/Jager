# DLT Ingestion Pipelines

This directory contains the Python scripts and configurations for data ingestion using **dlt** (Data Load Tool). 

The service is packaged inside the **`data-pipeline`** container service.

## Directory Structure

*   `olap/`: Contains scripts for ingesting data into OLAP target databases (e.g., MotherDuck).
    *   `ingest_buffer.py`: Syncs `s_buffer.channels` and `s_buffer.posts` from the PostgreSQL OLTP database to the MotherDuck OLAP database staging catalog using DLT's native schema evolution and merge logic.
*   `main.py`: A lightweight FastAPI service that exposes HTTP trigger endpoints (e.g., `POST /run/ingest_buffer`) which execute the ingestion scripts as subprocesses. This provides a secure way for external orchestrators (like **n8n**) to trigger scripts inside this container.
*   `Dockerfile` & `requirements.txt`: Container packaging and Python dependencies (including `dlt[duckdb,parquet]` and `pyarrow`).

---

## How to Run

### 1. Trigger via HTTP (Standard Orchestration / n8n)
Orchestrators can trigger ingestion pipelines securely via HTTP POST requests:
```bash
curl -X POST http://data-pipeline:8000/run/ingest_buffer
```
Returns a JSON payload with stdout, stderr, and execution status.

### 2. Run via CLI (Manual Execution / Debugging)
To run an ingestion pipeline manually as a pure CLI script inside the container:
```bash
docker compose exec data-pipeline python olap/ingest_buffer.py
```

---

## Configuration & Environment Variables

The container requires the following environment variables (defined in `docker-compose.yml`):
- `DATABASE_URL`: Connection string for the source PostgreSQL database.
- `MOTHERDUCK_TOKEN`: Token credential to write to MotherDuck.
- `MOTHERDUCK_DATABASE`: Target Motherduck database name (defaults to `staging`).
