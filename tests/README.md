# Tests Guide & Conventions

This directory contains unit and integration tests for Python data pipelines, ML services, Node.js scripts, and database operations.

## Running Tests

All Python unit tests are run using `pytest` via `uv`:

```bash
DATABASE_URL=postgresql://jager:jager@localhost:5432/jager uv run pytest tests/
```

## Test Files Overview

- **`test_seed_ingestion.py`**: Verifies seed file ingestion from `data/seed/` (`subscribers.csv`, `leads.json`) via `src/data_pipelines/oltp/ingest_seeds.py` into `cdp.leads`, `cdp.persons`, `cdp.client_accounts`, `cdp.person_account_relationships`, and `cdp.engagements`.
- **`test_dlt_ingestion.py`**: Unit tests for dlt ingestion pipelines and Motherduck integration mocks.
- **`test_ml.py`**: Tests ML prediction pipeline data formatting and features.
- **`test_utils.py`**: Tests database connection helper functions, HTTP header generation, and dlt pipeline initializers.
