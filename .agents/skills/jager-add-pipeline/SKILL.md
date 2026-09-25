---
name: jager-add-pipeline
description: >-
  Use this skill when the user wants to add a new dlt ingestion pipeline in
  Jager (OLAP, OLTP, or Reverse ETL), expose it via the dapp FastAPI service,
  or trigger it from an n8n workflow. Also covers manual data ingestion scripts
  targeting MotherDuck with staging/production safety conventions.
---

# Jager — Adding a dlt Data Pipeline

All ingestion pipelines use **dlt** (data load tool). Pipelines live under
`src/dapp/olap/` (OLAP → MotherDuck) or `src/dapp/oltp/` (OLTP → PostgreSQL).

---

## Step 1 — Create the Pipeline Script

### OLAP pipeline (PostgreSQL → MotherDuck)

Follow the pattern from `src/dapp/olap/ingest_linkedin.py`:

```python
# src/dapp/olap/ingest_mysource.py
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
- Always use `create_motherduck_pipeline()` from `common.utils` — never inline the logic.
- `dataset_name` = source schema name in PostgreSQL (controls target schema in MotherDuck).
- `write_disposition="merge"` with an explicit `primary_key` for OLAP ingestion.
- Set `SCHEMA__MAX_TABLE_NESTING = "0"` before creating any dlt pipeline.
- Use `write_disposition="replace"` only for Reverse ETL resources.
- Pin all dependencies to exact versions in `requirements.txt` / `pyproject.toml`.

---

## Step 2 — Expose via dapp FastAPI Service

Open `src/dapp/main.py` and add a POST endpoint:

```python
@app.post("/run/ingest_mysource")
async def run_ingest_mysource():
    result = subprocess.run(
        ["python", "-m", "olap.ingest_mysource"],
        capture_output=True, text=True, cwd="/app"
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
```

Naming convention:
- `/run/<pipeline_name>` for OLAP pipelines.
- `/run/oltp/<pipeline_name>` for OLTP pipelines.

---

## Step 3 — Trigger from n8n

In n8n, add an HTTP Request node:
- Method: `POST`
- URL: `{{ $env.DATA_PIPELINE_URL }}/run/ingest_mysource`
- No body required for trigger-only pipelines.

Add any new API keys or secrets to the `n8n` service's `environment` block in `docker-compose.yml`.

---

## Step 4 — Reverse ETL (MotherDuck → PostgreSQL)

If the pipeline reads from `t_jager` and writes back to PostgreSQL:

```python
# In src/dapp/olap/reverse_etl.py
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
# Test location
tests/dapp/test_ingest_mysource.py
```

Tests must verify:
- DB connection mocks work correctly.
- Transformations produce expected output shapes.
- API endpoint returns correct status codes.
- Key column mappings are preserved.

Run with: `uv run pytest tests/dapp/`

---

## Step 7 — Docker & Environment

Ensure `docker-compose.yml` has any new env vars in the `dapp` service `environment:` block:

```yaml
dapp:
  environment:
    - MYSOURCE_API_KEY=${MYSOURCE_API_KEY}
```

The `.env` file is for **local dev only** — never deploy it.

---

## Key Reference Files

| File | Purpose |
|------|---------|
| [`src/dapp/main.py`](../../src/dapp/main.py) | dapp FastAPI service with pipeline endpoints |
| [`src/dapp/common/utils.py`](../../src/dapp/common/utils.py) | `create_motherduck_pipeline()` helper |
| [`src/dapp/olap/`](../../src/dapp/olap/) | OLAP pipeline scripts |
| [`src/dapp/oltp/`](../../src/dapp/oltp/) | OLTP pipeline scripts |
| [`docker-compose.yml`](../../docker-compose.yml) | Service definitions + env vars |
| [`AGENTS.md`](../../AGENTS.md) | Full Jager coding conventions (dlt, Reverse ETL, env) |
