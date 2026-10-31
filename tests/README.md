# Tests Guide & Conventions

This directory contains unit and integration tests for Python data pipelines, ML components, shared core libraries, Node.js scripts, and database operations.

For test execution conventions, see the [Agent Conventions Guide](../AGENTS.md).

---

## 📁 Directory Structure

- **`shared/`**: Unit tests for the shared core library ([`test_shared.py`](shared/test_shared.py)).
- **`integration/`**: Integration tests, n8n workflow schema checks, and Docker build verifications ([`test-dockerfile.js`](integration/test-dockerfile.js), [`test_notion_workflow_schema.py`](integration/test_notion_workflow_schema.py)).
- **`fixtures/`**: Shared test fixtures and seeds.

---

## 🧪 Running Tests

```bash
# Run all Python tests across all domains
DATABASE_URL=postgresql://jager:jager@localhost:5432/jager uv run pytest tests/

# Pipeline / dbt / ML tests: run in the DAPP repo (uv run pytest)

# Run Shared library tests only
uv run pytest tests/shared/

# Run Dockerfile integration verification
node tests/integration/test-dockerfile.js
```
