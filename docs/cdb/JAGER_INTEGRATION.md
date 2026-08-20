# CDB — Jager Integration & Cutover Guide

**Version**: 0.1 (Draft)
**Status**: Under Review
**Last Updated**: 2026-08-20

> This document defines how Jager and CDB integrate, which Jager components must be updated during the cutover, and the exact cutover sequence to migrate without breaking running workflows.

---

## 1. Deployment Model

CDB is distributed as a **Docker image published to GitHub Container Registry (GHCR)**. Jager's `docker-compose.yml` pulls the image directly — no cross-stack networking, no separate compose file to manage.

```
CDB repo (GitHub)
  └── push to main
        └── GitHub Actions: build → push ghcr.io/data-biz-ai-consultancy/cdb:production

Jager VPS
  └── docker-compose.yml
        └── cdb-api:   image: ghcr.io/data-biz-ai-consultancy/cdb:production
        └── cdb-db:    image: postgres:16
        (both on the same jager_network as n8n)
```

**Integration principles:**
- CDB is the **source of truth** for all person and company data
- Jager pulls the latest `production`-tagged image on each `docker compose pull && docker compose up -d`
- n8n calls CDB over the internal Docker network: `http://cdb-api:8000`
- Service-to-service calls use a dedicated API key (`X-API-Key` header), not a user JWT

---

## 2. Current Jager CDP Endpoints (To Be Replaced)

The following endpoints are currently called by Jager's n8n workflows against `http://cdp:8000`:

| Endpoint | Called by | Purpose |
|----------|-----------|---------|
| `POST /process/linkedin_connections` | `cdp_lead_processing.json` | Ingest LinkedIn connections → `cdp.persons_linkedins` |
| `POST /process/manual_data` | `cdp_lead_processing.json` | Ingest manual data → `cdp.persons_manual_substack`, `cdp.leads_manual` |
| `POST /process/linkedin_messages` | `cdp_lead_processing.json` | Ingest LinkedIn messages → `cdp.leads_linkedin` |
| `POST /process/notion_meeting_notes` | `cdp_lead_processing.json` | Ingest Notion meeting notes → `cdp.activities_notion_meeting_notes` |
| `POST /process/evaluate_segments` | `cdp_lead_processing.json` | Refresh person/lead segment assignments |

---

## 3. New CDB Endpoint Mapping

| Old Jager CDP endpoint | New CDB endpoint | Notes |
|------------------------|-----------------|-------|
| `POST /process/linkedin_connections` | `POST /api/v1/ingest/linkedin-connections` | Same payload shape; requires `X-API-Key` header |
| `POST /process/manual_data` | `POST /api/v1/ingest/manual` | Multipart form now; `entity_type` + `column_map` required |
| `POST /process/linkedin_messages` | `POST /api/v1/ingest/linkedin-messages` | Same payload shape |
| `POST /process/notion_meeting_notes` | `POST /api/v1/ingest/notion-meeting-notes` | Same payload shape |
| `POST /process/evaluate_segments` | *(Phase 4 — deferred)* | Segment evaluation stays in Jager until Phase 4 |

---

## 4. Jager Changes Required

### 4.1 CDB repo — GitHub Actions (CI/CD)

CDB follows the same **train deployment model** as Jager:

| Trigger | Tag pushed | Environment |
|---------|-----------|-------------|
| Merge to `main` (automatic) | `staging`, `sha-<commit>` | Staging |
| Manual `workflow_dispatch` (explicit) | `production` | Production |

Merging to `main` alone **does not release to production**. A production release requires a deliberate manual trigger.

**Workflow 1 — CI Build** (`.github/workflows/ci.yml` in the CDB repo):

```yaml
name: CI — Build & Push Staging
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: |
            ghcr.io/data-biz-ai-consultancy/cdb:staging
            ghcr.io/data-biz-ai-consultancy/cdb:sha-${{ github.sha }}
```

**Workflow 2 — Release to Production** (`.github/workflows/release.yml` in the CDB repo):

```yaml
name: Release — Promote to Production
on:
  workflow_dispatch:
    inputs:
      sha:
        description: "Commit SHA to promote (leave blank for latest main)"
        required: false
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Retag staging → production
        run: |
          SHA="${{ github.event.inputs.sha || github.sha }}"
          docker pull ghcr.io/data-biz-ai-consultancy/cdb:sha-${SHA}
          docker tag  ghcr.io/data-biz-ai-consultancy/cdb:sha-${SHA} \
                      ghcr.io/data-biz-ai-consultancy/cdb:production
          docker push ghcr.io/data-biz-ai-consultancy/cdb:production
```

> **To release**: go to the CDB repo → Actions → "Release — Promote to Production" → Run workflow. Optionally specify a SHA to promote a specific commit rather than the latest.


### 4.2 Jager `docker-compose.yml`

Add `cdb-api` and `cdb-db` services pulling from GHCR. Both join the existing `jager_network` so n8n can reach `cdb-api` by container name:

```yaml
services:
  # ... existing Jager services ...

  cdb-api:
    image: ghcr.io/data-biz-ai-consultancy/cdb:production
    container_name: cdb-api
    restart: unless-stopped
    environment:
      DATABASE_URL: "postgresql://cdb:cdb@cdb-db:5432/cdb"
      CDB_API_KEY: "${CDB_API_KEY}"
      SECRET_KEY: "${CDB_SECRET_KEY}"
    depends_on:
      - cdb-db
    networks:
      - jager_network
    ports:
      - "8001:8000"     # host port 8001 to avoid conflict with dapp on 8000

  cdb-db:
    image: postgres:16
    container_name: cdb-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: cdb
      POSTGRES_USER: cdb
      POSTGRES_PASSWORD: cdb
    volumes:
      - cdb_db_data:/var/lib/postgresql/data
    networks:
      - jager_network
    ports:
      - "5433:5432"     # host port 5433; Jager's Postgres is on 5432

volumes:
  # ... existing volumes ...
  cdb_db_data:
```

> **To upgrade CDB**: `docker compose pull cdb-api && docker compose up -d cdb-api` — pulls the latest `production` image with no downtime for other services.

### 4.3 Jager `.env`

Add:
```
CDB_API_KEY=<generated_service_token>
CDB_SECRET_KEY=<generated_secret_key>
```

Generate both:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4.4 Jager `docker-compose.yml` — n8n env vars

Add to the `n8n` service's `environment` block:
```yaml
CDB_API_URL: "http://cdb-api:8000"
CDB_API_KEY: "${CDB_API_KEY}"
```

---

## 5. n8n Workflow Updates

### Workflow: `cdp_lead_processing.json`

This is the only n8n workflow that calls CDP endpoints. It runs every 6 hours.

For each HTTP Request node, update:

| Node | Old URL | New URL | Header to add |
|------|---------|---------|---------------|
| Ingest LinkedIn Connections | `={{ $env.CDP_SERVICE_URL }}/process/linkedin_connections` | `={{ $env.CDB_API_URL }}/api/v1/ingest/linkedin-connections` | `X-API-Key: {{ $env.CDB_API_KEY }}` |
| Ingest Manual Data | `={{ $env.CDP_SERVICE_URL }}/process/manual_data` | `={{ $env.CDB_API_URL }}/api/v1/ingest/manual` | `X-API-Key: {{ $env.CDB_API_KEY }}` |
| Ingest LinkedIn Messages | `={{ $env.CDP_SERVICE_URL }}/process/linkedin_messages` | `={{ $env.CDB_API_URL }}/api/v1/ingest/linkedin-messages` | `X-API-Key: {{ $env.CDB_API_KEY }}` |
| Ingest Notion Meeting Notes | `={{ $env.CDP_SERVICE_URL }}/process/notion_meeting_notes` | `={{ $env.CDB_API_URL }}/api/v1/ingest/notion-meeting-notes` | `X-API-Key: {{ $env.CDB_API_KEY }}` |
| Evaluate Segments | `={{ $env.CDP_SERVICE_URL }}/process/evaluate_segments` | **Keep calling Jager CDP for now** (Phase 4) | No change |

### Workflow: `cdp_weekly_network_review.json`

This workflow reads from `s_motherduck` PostgreSQL views (not CDP endpoints directly). **No changes needed** for the cutover — the Reverse ETL pipeline from Motherduck remains unaffected.

> After Phase 1 of CDB is stable, update the Reverse ETL pipeline to read from CDB's PostgreSQL instead of `s_motherduck`.

---

## 6. Jager CDP Service — Deprecation Plan

| Phase | Action |
|-------|--------|
| **Before cutover** | Keep `cdp` service running in parallel |
| **Day 0 (cutover)** | Update n8n nodes to point to CDB; run both services simultaneously |
| **Day 0 + 24h** | Verify all n8n executions successful in CDB; no errors in Jager CDP logs |
| **Day 0 + 7d** | Stop the `cdp` service in `docker-compose.yml` (`profiles: [legacy]`) |
| **Day 0 + 14d** | Remove `src/cdp/` from Jager repo in a separate PR |
| **Day 0 + 14d** | Archive Jager's `cdp` PostgreSQL database (pg_dump → S3) |

> **Never drop** the Jager `cdp` database until the archive is confirmed and at least one full Reverse ETL cycle has completed successfully from CDB.

---

## 7. Data Flow After Cutover

```
                 Every 6 hours (n8n scheduled)
                           │
         ┌─────────────────┼─────────────────────┐
         │                 │                     │
         ▼                 ▼                     ▼
 POST /ingest/      POST /ingest/       POST /ingest/
 linkedin-          manual              notion-
 connections                            meeting-notes
         │                 │                     │
         └────────────────►│◄────────────────────┘
                           ▼
                   CDB Entity Resolution
                    (incremental run)
                           │
              ┌────────────┴──────────────┐
              ▼                           ▼
        persons (master)           er_candidate_pairs
                                    (review queue)
                           │
                           ▼
               Reverse ETL (Motherduck)
               → s_motherduck in Jager
               → Slack weekly digest
```

---

## 8. Service-to-Service Authentication

CDB exposes ingestion endpoints under `/api/v1/ingest/*` with API key auth (not user JWT). This key is static and stored in both Jager's `.env` and CDB's `.env`.

Generate a secure key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Store as `CDB_API_KEY` in both `.env` files.

CDB validates the key on ingestion endpoints via a FastAPI dependency:
```python
async def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.CDB_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

---

*See [DATA_MIGRATION.md](DATA_MIGRATION.md) for the database migration steps that must happen before this cutover.*
