---
name: jager-ml-pipeline
description: >-
  Historical note: Jager `src/dapp/ml/` was removed with the DAPP split. ML
  under DAPP `src/ml/` is also retired — no active use case. Do not re-add
  without an explicit product decision.
---

# Jager Machine Learning & Prediction Pipelines — retired

**Status:** Jager no longer ships a data-plane tree (`src/dapp/` deleted). Canonical
FastAPI, MotherDuck features, and any future ML live in **[DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP)**.
DAPP `src/ml/` is **not** in the tree today (LinkedIn timeslot and stock predict routes removed).

If ML returns later:

1. Implement under **DAPP** `src/ml/<use_case>/` (1 use case, 1 subfolder) — see [dapp-ml-pipeline](https://github.com/Data-Biz-AI-Consultancy/DAPP/blob/main/.agents/skills/dapp-ml-pipeline/SKILL.md) when restored.
2. Mount inference with `X-API-Key` on `dapp-api`; n8n in Jager calls `ML_SERVICE_URL` / `DATA_PIPELINE_URL` (`http://dapp-api:8000`).
3. Add or restore n8n workflows under `src/n8n/workflows/ml/` only after DAPP routes exist.
4. Run tests in **DAPP** (`uv run pytest`), not in Jager.

Related: [`jager-add-pipeline`](jager-add-pipeline/SKILL.md), [`jager-cdb-integration`](jager-cdb-integration/SKILL.md), [`jager-release-and-deployment`](jager-release-and-deployment/SKILL.md).
