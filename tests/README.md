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
You can run the Python unit tests using `pytest` and `uv` (recommended):

```bash
uv run --with pytest --with scikit-learn --with pandas --with fastapi --with httpx --with numpy pytest tests/test_ml.py
```
