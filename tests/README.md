# Tests Guide & Conventions

This directory contains unit and integration tests for Python data pipelines, ML components, shared core libraries, Node.js scripts, and database operations.

For test execution conventions, see the [Agent Conventions Guide](../AGENTS.md).

---

## 📁 Directory Structure

- **`dapp/`**: Unit tests for Data App services, including ingestion pipelines, ML modules, and utilities ([`test_dlt_ingestion.py`](dapp/test_dlt_ingestion.py), [`test_ml.py`](dapp/test_ml.py), [`test_utils.py`](dapp/test_utils.py)).
- **`shared/`**: Unit tests for the shared core library ([`test_shared.py`](shared/test_shared.py)).
- **`integration/`**: Integration tests and Docker build verifications ([`test-dockerfile.js`](integration/test-dockerfile.js)).
- **`fixtures/`**: Shared test fixtures and seeds.

---

## 🧪 Running Tests

```bash
# Run all Python tests across all domains
DATABASE_URL=postgresql://jager:jager@localhost:5432/jager uv run pytest tests/

# Run Data App (dapp) tests only (includes dlt pipelines & ML)
uv run pytest tests/dapp/

# Run Shared library tests only
uv run pytest tests/shared/

# Run Dockerfile integration verification
node tests/integration/test-dockerfile.js
```
