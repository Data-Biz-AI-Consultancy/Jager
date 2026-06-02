# Jager Backend Unit Tests

This folder contains unit tests for the Jager FastAPI backend. Tests are executed using an in-memory SQLite database so they do not conflict with or write to your live PostgreSQL database.

## Running Tests Locally

You can run the tests in two ways:

### Via Docker (Recommended)

Since the backend is containerized with all dependencies pre-installed, you can run the test suite directly inside the running container:

```bash
uv run pytest
```

---

