---
name: jager-release-and-deployment
description: >-
  Use this skill when cutting a release or troubleshooting deployments across the
  tri-repo ecosystem: Jager (core automation/n8n/dapp), cdb (Customer Data Platform/CRM),
  and Jager-Deployment (private GitOps self-hosted runner). Covers semantic release triggers,
  repository_dispatch events, shared Docker bridge networking (`jager_network`), port allocations,
  and production environment secrets injection.
---

# Jager, CDB & Jager-Deployment Release & GitOps Architecture

Jager, CDB, and Jager-Deployment operate as an integrated tri-repo ecosystem:

```
┌─────────────────────────┐          ┌─────────────────────────┐
│       Jager (OSS)       │          │        CDB (OSS)        │
│  - n8n Workflows        │          │  - FastAPI Backend      │
│  - dapp (dlt/dbt/ml)    │          │  - Next.js 15 Frontend  │
│  - PostgreSQL (5432)    │          │  - PostgreSQL (5433)    │
└────────────┬────────────┘          └────────────┬────────────┘
             │ Semantic Release                   │ Semantic Release (GHCR Multi-Arch)
             │ repository_dispatch                │
             ▼                                    ▼
┌──────────────────────────────────────────────────────────────┐
│            Jager-Deployment (Private GitOps Repo)            │
│  - Runs on Self-Hosted VPS Runner                            │
│  - Checks out Jager (tagged) + CDB (main)                    │
│  - Deploys on shared `jager_network` bridge                  │
│  - Injects production secrets (MotherDuck, Cloudflare Tunnel)│
│  - Auto-executes CDB Alembic migrations                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. Release Flow Step-by-Step

### Step 1: Cutting a Jager Release
1. Push or merge Conventional Commits to `main` in `Jager`.
2. Trigger the release workflow in `Jager/.github/workflows/release.yml` (via `workflow_dispatch` or push):
   - Builds custom n8n Docker image.
   - Runs `semantic-release` to create a new Git tag (`vX.Y.Z`) and GitHub Release.
   - Sends a `repository_dispatch` webhook to `Data-Biz-AI-Consultancy/Jager-Deployment` with `event_type: deploy-release`, passing the new release `version`, `tag`, and `token`.

### Step 2: Cutting a CDB Release
1. Push or merge Conventional Commits to `main` in `cdb`.
2. `.github/workflows/release.yml` triggers automatically:
   - Computes semver bump (`patch`/`minor`/`major`).
   - Builds native `linux/amd64` and `linux/arm64` container images.
   - Pushes multi-arch manifests to GitHub Container Registry (`ghcr.io/data-biz-ai-consultancy/cdb-backend`, `cdb-frontend`) tagged `vX.Y.Z` and `production`.

### Step 3: Deployment Execution (`Jager-Deployment`)
The self-hosted runner executes `.github/workflows/deploy.yml`:
1. **Repository Checkouts**:
   - Checks out `Jager` at the triggered release tag into `./jager`.
   - Checks out `cdb` at `main` into `./cdb`.
2. **Network Setup**:
   - Ensures the shared Docker bridge network `jager_network` exists.
3. **Port De-confliction**:
   - Stops existing containers from both project stacks (`jager-main` and `cdb`).
   - Force-frees ports `80`, `443`, `3001`, `5432`, `5433`, `6380`, `8000`, `8001`.
4. **Volume Migration**:
   - Ensures legacy volumes (`jager-deployment_*`) are migrated to `jager_*`.
5. **Stack Deployment**:
   - Starts Jager: `sudo -E docker compose -p jager-main --profile all up -d --build --remove-orphans`.
   - Starts CDB: `sudo -E docker compose -p cdb up -d --build --remove-orphans`.
6. **Database Migrations**:
   - Automatically executes CDB Alembic migrations:
     ```bash
     sudo docker compose -p cdb exec -T cdb-api alembic -c db/alembic.ini upgrade head
     ```

---

## 2. Port & Network Allocation Matrix

| Service | Stack | Host Port | Internal Docker URL | Description |
|---------|-------|-----------|---------------------|-------------|
| **Caddy Proxy** | Jager | `80`, `443` | `caddy` | Reverse proxy & SSL termination |
| **N8N** | Jager | `5678` | `http://n8n:5678` | Workflow orchestration UI & API |
| **Jager Postgres** | Jager | `5432` | `db:5432` | OLTP operational database (`jager`, `n8n`) |
| **DAPP (ETL/ML)** | Jager | `8000` (internal) | `http://data-pipeline:8000` | dlt, dbt, and ML prediction endpoints |
| **CDB Postgres** | CDB | `5433` | `cdb-db:5432` | Standalone CRM PostgreSQL 16 database |
| **CDB Redis** | CDB | `6380` | `cdb-redis:6379` | Celery task queue & cache |
| **CDB API** | CDB | `8001` (or `8000`) | `http://cdb-api:8000` | FastAPI Customer Data Platform endpoints |
| **CDB Frontend** | CDB | `3001` | `http://cdb-frontend:3000` | Next.js 15 App Router web client |

---

## 3. Production Environment Secrets

Injected dynamically during deployment from `Jager-Deployment` GitHub Secrets:

- **Analytics / OLAP**: `MOTHERDUCK_TOKEN`, `MOTHERDUCK_DATABASE=production`.
- **Integrations**: `NOTION_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `SLACK_OAUTH_TOKEN`, `BUFFER_API_KEY`.
- **Networking & Access**: `TUNNEL_TOKEN` (Cloudflare Tunnel).
- **Service Authentication**: `CDB_API_KEY` (shared between Jager n8n and CDB API), `CDB_SECRET_KEY` (JWT signing).

---

## 4. Manual Deployment & Rollback Runbook

To trigger or roll back a specific version manually:

1. Go to `Data-Biz-AI-Consultancy/Jager-Deployment` on GitHub.
2. Select **Actions** $\rightarrow$ **Deploy Release** $\rightarrow$ **Run workflow**.
3. Input the desired Git tag:
   - To promote a release: `tag = v1.2.0`
   - To roll back: `tag = v1.1.0`
4. Verify execution logs on the self-hosted runner.
5. Check health:
   ```bash
   curl http://localhost:8000/healthz   # CDB API
   curl http://localhost:5678/healthz  # N8N
   ```
