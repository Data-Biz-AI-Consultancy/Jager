# DAPP code moved

All former contents of this directory (`olap/`, `oltp/`, `dbt/`, `ml/`, FastAPI `main.py`, Dockerfile) now live in the **[DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP)** repository.

Jager only orchestrates via n8n → authenticated HTTP:

- Image: `ghcr.io/data-biz-ai-consultancy/dapp` (see [`docker-compose.dapp.yml`](../../docker-compose.dapp.yml))
- Base URL: `DATA_PIPELINE_URL` / `ML_SERVICE_URL` / `OLTP_PIPELINE_URL` → `http://dapp-api:8000`
- Auth: `X-API-Key: $DAPP_API_KEY`

Do not add pipeline or ML code here — open a PR against DAPP instead.
