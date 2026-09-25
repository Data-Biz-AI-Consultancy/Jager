---
name: jager-ml-pipeline
description: >-
  Use this skill when developing, training, or deploying Machine Learning models in Jager
  (e.g., optimal publishing timeslot recommendation, engagement prediction), managing
  feature pipelines in MotherDuck, exposing inference via the dapp FastAPI service, or writing ML unit tests.
---

# Jager Machine Learning & Prediction Pipelines

Machine learning services live under [`src/dapp/ml/`](../../src/dapp/ml/) and are executed within the `dapp` Docker container.

---

## 1. Directory Structure & Architecture

Follow the **1 use case, 1 subfolder** rule:

```
src/dapp/ml/
├── timeslot_recommendation/   ← Dedicated subfolder per use case
│   ├── features.py            ← Feature extraction & aggregation from MotherDuck
│   ├── train.py               ← Model training, validation & serialization
│   ├── predict.py             ← Inference pipeline
│   └── evaluate.py            ← Model evaluation metrics & drift checks
└── common/                    ← Shared ML utilities (scalers, encoders, duckdb helpers)
```

Never place standalone use-case scripts directly in the root of `src/dapp/ml/`.

---

## 2. Feature Extraction from MotherDuck

Features are sourced from curated marts and staging datasets in MotherDuck:

```python
import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

def extract_training_features():
    token = os.environ["MOTHERDUCK_TOKEN"]
    db = os.environ.get("MOTHERDUCK_DATABASE", "staging")
    conn = duckdb.connect(f"md:{db}?motherduck_token={token}")
    
    df = conn.execute("""
        SELECT * FROM marts.fct_linkedin_personal_account_post_engagement
    """).fetchdf()
    conn.close()
    return df
```

---

## 3. Exposing Inference via FastAPI (`src/dapp/main.py`)

Add a POST endpoint to allow n8n or Celery to trigger training or inference:

```python
@app.post("/predict/timeslot_recommendation")
async def run_timeslot_prediction():
    result = subprocess.run(
        ["python", "-m", "ml.timeslot_recommendation.predict"],
        capture_output=True, text=True, cwd="/app"
    )
    return {"status": "success", "stdout": result.stdout, "stderr": result.stderr}
```

---

## 4. Writing Unit Tests

All ML components must have unit tests with mocked database connections:

```bash
# Test location
tests/dapp/ml/test_timeslot_recommendation.py

# Run tests
uv run pytest tests/dapp/
```
