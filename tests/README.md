# Tests

This directory contains automated unit tests for the Jager project.

## Running Tests Locally

### Node.js Tests
You can run the unit tests directly using Node.js:

```bash
# Verify that all COPY source paths in the Dockerfile exist in the project root context
node tests/test-dockerfile.js
```

### Python ML Backend Tests
You can run the Python unit tests using `pytest` and `uv` targeting the `tests/` folder:

```bash
uv run pytest tests/
```
