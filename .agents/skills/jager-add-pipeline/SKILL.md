---
name: jager-add-pipeline
description: >-
  Use this skill when the user wants to add a new dlt ingestion pipeline in
  Jager (OLAP, OLTP, or Reverse ETL), expose it via the dapp FastAPI service,
  or trigger it from an n8n workflow. Also covers manual data ingestion scripts
  targeting MotherDuck with staging/production safety conventions.
---

# Jager — Adding a dlt Data Pipeline

> **Runtime owner:** New pipelines and FastAPI `/run/*` routes belong in the **[DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP)** repo (`src/olap/data_ingestion/`, `src/api/`). Deploy via GHCR + [`docker/docker-compose.production.yml`](https://github.com/Data-Biz-AI-Consultancy/DAPP/blob/main/docker/docker-compose.production.yml). Jager n8n triggers `http://dapp-api:8000` with `X-API-Key: $DAPP_API_KEY`. Steps below describe patterns; implement pipeline code and `/run` routes in **DAPP**, then add an n8n HTTP trigger in Jager.

Historical copies may still exist under retired `src/dapp/` paths in Jager — treat those as reference only. Live MotherDuck OLAP pipelines live in DAPP.
> **Runtime owner:** New pipelines and FastAPI `/run/*` routes belong in the **[DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP)** repo (`src/olap/data_ingestion/`, `src/api/`). Deploy via GHCR + [`docker/docker-compose.production.yml`](https://github.com/Data-Biz-AI-Consultancy/DAPP/blob/main/docker/docker-compose.production.yml). Jager n8n triggers `http://dapp-api:8000` with `X-API-Key: $DAPP_API_KEY`. Steps below describe the historical Jager layout for reference.

All ingestion pipelines use **dlt** (data load tool). Legacy copies may live under
`src/dapp/olap/` (OLAP → MotherDuck) or `src/dapp/oltp/` (OLTP → PostgreSQL).

---

## Step 1 — Create the Pipeline Script (in DAPP)

### OLAP pipeline (PostgreSQL → MotherDuck)

Follow the pattern from DAPP `src/olap/data_ingestion/ingest_linkedin.py` (or the historical Jager `src/dapp/olap/ingest_linkedin.py` if still present locally):

```python
# DAPP: src/olap/data_ingestion/ingest_mysource.py
import os
from common.utils import create_motherduck_pipeline
import dlt
from sqlalchemy import create_engine, text

os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"  # ALWAYS set this

def mysource_resource(engine):
    @dlt.resource(
        write_disposition="merge",
        primary_key="id",
        name="mysource_records",
    )
    def load_mysource():
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT * FROM s_mysource.records")).mappings()
            yield from rows
    return load_mysource

def run_ingestion():
    from dotenv import load_dotenv
    load_dotenv()
    engine = create_engine(os.environ["DATABASE_URL"])
    pipeline = create_motherduck_pipeline(dataset_name="s_mysource")
    pipeline.run(mysource_resource(engine))
    print("Done.")

if __name__ == "__main__":
    run_ingestion()
```

**Key rules**:
- Always use `create_motherduck_pipeline()` from the DAPP common helpers — never inline the logic.
- `dataset_name` = source schema name in PostgreSQL (controls target schema in MotherDuck).
- `write_disposition="merge"` with an explicit `primary_key` for OLAP ingestion.
- Set `SCHEMA__MAX_TABLE_NESTING = "0"` before creating any dlt pipeline.
- Use `write_disposition="replace"` only for Reverse ETL resources.
- Pin all dependencies to exact versions in `requirements.txt` / `pyproject.toml`.

---

## Step 2 — Expose via DAPP FastAPI Service

In the DAPP repo, register a POST route (see `src/api/routes/olap.py`):

```python
@app.post("/run/ingest_mysource")
async def run_ingest_mysource():
    result = subprocess.run(
        ["python", "-m", "olap.data_ingestion.ingest_mysource"],
        capture_output=True, text=True, cwd="/app"
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
```

Naming convention:
- `/run/ingest_<name>` for MotherDuck OLAP pipelines.
- `/run/oltp/<pipeline_name>` for OLTP pipelines.
- `/run/connectors/<name>` for VectorDB connectors (not MotherDuck).

---

## Step 3 — Trigger from n8n (Jager)

In n8n, add an HTTP Request node (typeVersion 4.2):

- Method: `POST`
- URL: `={{ $env.DATA_PIPELINE_URL || 'http://dapp-api:8000' }}/run/ingest_mysource`
- Headers: `X-API-Key` = `={{ $env.DAPP_API_KEY }}` (`sendHeaders: true`)
- No body required for trigger-only pipelines.

Ensure `DATA_PIPELINE_URL` and `DAPP_API_KEY` are in the `n8n` service `environment` block in `docker-compose.yml`. Add any new pipeline-specific secrets to the **DAPP** service env, not only n8n.

MotherDuck schedule coverage is a single workflow: [`motherduck_data_ingestion_jager.json`](../../src/n8n/workflows/olap/data_ingestion/motherduck_data_ingestion_jager.json) (add a parallel HTTP Request node there for new MotherDuck ingest routes).

---

## Step 4 — Reverse ETL (MotherDuck → PostgreSQL)

If the pipeline reads from `t_jager` and writes back to PostgreSQL, implement the resource in **DAPP** reverse ETL (historical reference: `src/dapp/olap/reverse_etl.py`):

```python
# Add the new resource to the existing Reverse ETL pipeline
@dlt.resource(
    write_disposition="replace",
    name="my_t_jager_table",
)
def my_t_jager_resource(conn):
    rows = conn.execute("SELECT * FROM t_jager.my_table").fetchdf()
    yield rows.to_dict(orient="records")
```

Always use `dataset_name="s_motherduck"` for the Reverse ETL destination.
Always close the DuckDB connection in a `finally` block.

---

## Step 5 — Manual Ingestion Scripts (MotherDuck upload)

For one-off spreadsheet/CSV uploads targeting MotherDuck:

```python
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--prod", action="store_true")
args = parser.parse_args()

if args.prod:
    token = os.environ["MOTHERDUCK_TOKEN_PROD"]
    db = "production"
else:
    token = os.environ["MOTHERDUCK_TOKEN"]   # default: staging
    db = os.environ.get("MOTHERDUCK_DATABASE", "staging")
```

**Rule**: Always default to `staging`. Use `--prod` flag explicitly for production.

Table naming in `s_manual` schema:
```
<tool>__<child_page_prefix>_<entity_name>
# Example: notion__substack_subscriber_export_2026_07_30_11_46_53_csv
```

---

## Step 6 — Write Tests

```bash
# Test location (DAPP repo)
tests/… covering ingest_mysource
```

Tests must verify:
- DB connection mocks work correctly.
- Transformations produce expected output shapes.
- API endpoint returns correct status codes.
- Key column mappings are preserved.

In Jager historical suites: `uv run pytest tests/dapp/` (if still present). Prefer DAPP CI for new pipeline tests.

---

## Step 7 — Docker & Environment

Ensure DAPP compose / Jager-Deployment secrets include any new env vars for the **dapp-api** service:

```yaml
dapp-api:
  environment:
    - MYSOURCE_API_KEY=${MYSOURCE_API_KEY}
```

The `.env` file is for **local dev only** — never deploy it.

---

## Key Reference Files

| File | Purpose |
|------|---------|
| DAPP `src/api/routes/olap.py` | FastAPI `/run/ingest_*` MotherDuck routes |
| DAPP `src/olap/data_ingestion/` | MotherDuck OLAP pipeline scripts |
| [`src/n8n/workflows/olap/data_ingestion/`](../../src/n8n/workflows/olap/data_ingestion/) | n8n HTTP triggers (Jager) |
| [`docker-compose.yml`](../../docker-compose.yml) | n8n `DATA_PIPELINE_URL` + `DAPP_API_KEY` |
| [`AGENTS.md`](../../AGENTS.md) | Full Jager coding conventions |
