# Data pipelines & API (runtime: DAPP repo)

**Production and staging runtime** for the data-plane FastAPI service (`dapp-api`), VectorDB, and MotherDuck OLAP live in the **[DAPP](https://github.com/Data-Biz-AI-Consultancy/DAPP)** repository. Jager **does not** build that image from this folder.

- **Deploy:** [DAPP `docker/docker-compose.production.yml`](https://github.com/Data-Biz-AI-Consultancy/DAPP/blob/main/docker/docker-compose.production.yml) on shared `jager_network` with `DAPP_IMAGE_TAG=staging` or pinned `vX.Y.Z`.
- **Call from n8n:** `DATA_PIPELINE_URL=http://dapp-api:8000`, header `X-API-Key: $DAPP_API_KEY` (see root [`docker-compose.yml`](../../docker-compose.yml)).
- **Operator notes:** [`docker-compose.dapp.yml`](../../docker-compose.dapp.yml) in the Jager repo.

## Legacy tree under `src/dapp/`

Historical **dbt**, OLTP/OLAP docs, and pipeline scripts may remain here for reference while the canonical implementation moves in DAPP (`src/olap/`, `src/api/`). Do not add new FastAPI endpoints in Jager for orchestration — extend DAPP and redeploy the GHCR image.

### Related docs (legacy paths)

- [oltp/README.md](oltp/README.md) — OLTP schema notes
- [olap/README.md](olap/README.md) — OLAP / MotherDuck notes
- [ml/README.md](ml/README.md) — ML (mostly retired; active ML lives in DAPP policy)
