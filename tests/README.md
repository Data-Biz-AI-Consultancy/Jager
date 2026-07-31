# Tests Guide & Conventions

This directory contains unit and integration tests for Python data pipelines, CDP services, ML components, shared core libraries, Node.js scripts, and database operations organized into namespaced service subdirectories.

## Directory Structure

- **`cdp/`**: Unit tests for Customer Data Platform services ([test_cdp_processor.py](file:///Users/jimmypang/AntigravityProjects/Jager/tests/cdp/test_cdp_processor.py)).
- **`dapp/`**: Unit tests for Data App services, including ingestion pipelines, ML modules, and utilities ([test_dlt_ingestion.py](file:///Users/jimmypang/AntigravityProjects/Jager/tests/dapp/test_dlt_ingestion.py), [test_ml.py](file:///Users/jimmypang/AntigravityProjects/Jager/tests/dapp/test_ml.py), [test_seed_ingestion.py](file:///Users/jimmypang/AntigravityProjects/Jager/tests/dapp/test_seed_ingestion.py), [test_utils.py](file:///Users/jimmypang/AntigravityProjects/Jager/tests/dapp/test_utils.py)).
- **`shared/`**: Unit tests for the shared core library ([test_shared.py](file:///Users/jimmypang/AntigravityProjects/Jager/tests/shared/test_shared.py)).
- **`integration/`**: Integration tests and Docker build verifications ([test-dockerfile.js](file:///Users/jimmypang/AntigravityProjects/Jager/tests/integration/test-dockerfile.js)).
- **`fixtures/`**: Shared test fixtures (e.g. `fixtures/seed/`).

## Running Tests

Run all Python tests across all domains:

```bash
DATABASE_URL=postgresql://jager:jager@localhost:5432/jager uv run pytest tests/
```

Run tests for a specific service or domain:

```bash
# Run CDP tests only
uv run pytest tests/cdp/

# Run Data App (dapp) tests only (includes dlt pipelines & ML)
uv run pytest tests/dapp/

# Run Shared library tests only
uv run pytest tests/shared/
```

Run Dockerfile integration verification:

```bash
node tests/integration/test-dockerfile.js
```
