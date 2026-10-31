# Jager 🚀

Jager is an AI-native leads generator, simplified to use **N8N** as the primary orchestration engine and component.

## Features

- **AI-Native Lead Generation**: Automated ingestion and analysis of multiple channels (Reddit, Slack, Substack) using custom prompt templates (`prompts/`) for intent detection and lead enrichment.
- **Robust Ingestion Pipelines**: Leverages **dlt** (Data Load Tool) for transferring database stages into MotherDuck and **dbt** for transformations.
- **Machine Learning Integration**: Provides training and prediction pipelines targeting optimal LinkedIn publishing timeslots, managing model features and predictions in MotherDuck.
- **Flexible Local Development**: Complete containerized environment including PostgreSQL with pgvector, N8N, custom ML services, Caddy reverse proxy, and Cloudflare tunnels.
- **Workflow & Database Syncing**: Developer utility scripts for cloning production databases locally, migrating schemas, and keeping local workflow JSON files in sync with PostgreSQL.

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose installed.

### Run Locally

We use **Docker Compose Profiles** to allow spinning up only the services you need, saving RAM, CPU, and battery:

*   **App Stack** (n8n, Postgres, Caddy, Cloudflare Tunnel):
    ```bash
    docker-compose --profile app up --build -d
    ```
*   **External DAPP** (pull GHCR production/staging image + VectorDB; all pipelines live in the DAPP repo):
    ```bash
    export DAPP_IMAGE_TAG=v1.0.0   # or production / staging
    export DAPP_API_KEY=... MOTHERDUCK_TOKEN=... POSTGRES_PASSWORD=...
    # Sibling checkout of DAPP supplies sql/init (override with DAPP_SQL_INIT_PATH)
    docker compose -f docker-compose.yml -f docker-compose.dapp.yml \
      --profile app --profile dapp-external up -d
    ```
*   **Core Stack** (Postgres DB, Caddy, Tunnel):
    ```bash
    docker compose --profile core up -d
    ```
*   **All Services** (n8n/app only — DAPP via `dapp-external` or sibling DAPP compose):
    ```bash
    docker compose --profile all up --build -d
    ```

> [!TIP]
> You can also set `COMPOSE_PROFILES=app` (or `all`, `core`, `dapp-external`) in your `.env` file to default to a specific profile when running `docker compose up`.

n8n defaults: `DATA_PIPELINE_URL` / `ML_SERVICE_URL` → `http://dapp-api:8000` with `X-API-Key: $DAPP_API_KEY`. OLTP workflows use `OLTP_PIPELINE_URL` → `http://dapp:8000` (embedded) until those routes exist on the external image.

Access your local services:
- **N8N**: [http://localhost](http://localhost) (Staging: `https://staging.jager.n8n.com`, Production: `https://jager.n8n.com`)
- **CDB Frontend**: [http://localhost:3001](http://localhost:3001) (Staging: `https://staging.cdb.com`, Production: `https://cdb.com`)
- **CDB API**: [http://localhost:8001](http://localhost:8001) (OpenAPI Docs: [http://localhost:8001/docs](http://localhost:8001/docs))

---

## Architecture & Microservice Interactions

Jager is structured around central workflow orchestration and data applications, integrating with the standalone CDB service:

```mermaid
flowchart TD
    N8N["N8N Orchestration (src/n8n/)<br/>Workflow Scheduler & Orchestrator"]
    
    subgraph DecoupledServices["Standalone Services"]
        CDB["CDB Service (cdb)<br/>Customer Data Platform / CRM API"]
    end

    subgraph DataServices["Python Microservices & Services"]
        DAPPAPI["DAPP (GHCR dapp-api)<br/>MotherDuck OLAP + ML API"]
        DAPPAPI2["DAPP GHCR<br/>OLAP + OLTP + ML"]
    end
    
    subgraph Storage["Storage Layer"]
        PG[("PostgreSQL (db)<br/>OLTP Data & Staging Schemas")]
        MD[("MotherDuck<br/>OLAP Data & ds_* Datasets")]
        VDB[("DAPP VectorDB (dapp-db)<br/>m_* memory schemas")]
    end
    
    N8N -->|"HTTP POST /api/v1/ingest/*"| CDB
    N8N -->|"HTTP + X-API-Key /run/* & ML"| DAPPAPI
    N8N -->|"HTTP /run/oltp/*"| DAPPAPI
    
    DAPPAPI -->|"REST API Sync"| CDB
    DAPPAPI -->|"SOURCE_DATABASE_URL"| PG
    DAPPAPI -->|"Sync OLAP / ML"| MD
    DAPPAPI --> VDB
```

*   **N8N Orchestration (`src/n8n/`)**: Serves as the central job orchestrator (operating like an AI-native Airflow) to schedule, trigger, and coordinate automated workflows via HTTP endpoints.
*   **CDB Standalone Service**: Customer Data Platform & CRM service managing contacts, companies, and interactions. Direct channel integrations (such as LinkedIn messages and connections, and Notion meeting notes) are ingested natively by CDB's background connector service with full timestamp fidelity, while external webhooks and partner tools ingest via CDB API endpoints (`CDB_SERVICE_URL`) using API key authentication (`CDB_API_KEY`).
*   **External DAPP (`dapp-api`)**: Prefer the GHCR image via [`docker-compose.dapp.yml`](docker-compose.dapp.yml) (`DAPP_IMAGE_TAG=v1.0.0` / `production`). N8N triggers MotherDuck pipelines and ML with `DATA_PIPELINE_URL` / `ML_SERVICE_URL` and `DAPP_API_KEY`.
*   **DAPP code**: moved out of Jager — see [`src/dapp/README.md`](src/dapp/README.md) and the DAPP repo.

### Database & Storage Schemas

We organize our databases into clear operational (OLTP) and analytical (OLAP) processing schemas:
- **OLTP Schema (PostgreSQL)**: ops `s_*` / `t_*` in Jager Postgres; writers are DAPP `/run/oltp/*`.
- **OLAP Schema (MotherDuck)**: owned by DAPP (`src/olap`, `src/dbt` in the DAPP repo).

---

## Folder Structure

Below is the directory layout and overview of the Jager repository:

```text
jager/
├── caddy/                   # Caddy reverse proxy configuration (Caddyfile)
├── data/                    # Data storage (e.g., raw LinkedIn spreadsheets)
├── prompts/                 # Markdown prompt templates (intent detection, lead enrichment)
├── scripts/                 # Utility scripts for database cloning, schema migrations, and data import
├── src/                     # Core application source code
│   ├── dapp/                # Data App (Ingestion, dbt transformations, and ML microservice)
│   ├── db/                  # Database initialization scripts
│   └── n8n/                 # N8N configuration, workflow files, and sync scripts
└── tests/                   # Automated Node.js and Python unit test suites
```

Refer to the folder-level READMEs for detailed guides:
- [scripts/README.md](scripts/README.md)
- [src/db/README.md](src/db/README.md)
- [src/dapp/README.md](src/dapp/README.md)
- [tests/README.md](tests/README.md)


### Important Root Files

*   **`docker-compose.yml`**: Configures and runs all local service containers (`db`, `n8n`, `ml`, `data-pipeline`, `caddy`, and `tunnel`).
*   **`AGENTS.md`**: Contains agent rules, naming conventions, coding styles, and project constraints.
*   **`package.json` / `pnpm-lock.yaml`**: Node dependencies and configuration for utility and synchronization scripts.
*   **`.releaserc.json`**: Semantic release configuration.
*   **`.env`**: Local environment variables configuration.

---

## 🧭 Documentation & Skills Index

Operational runbooks and technical guidelines are codified under [`.agents/skills/`](.agents/skills/):

| Area | Skill / Document | Description |
|------|------------------|-------------|
| **dbt Modeling** | [`jager-dbt-model`](.agents/skills/jager-dbt-model/SKILL.md) | Layer conventions (`staging`, `intermediate`, `marts`, `t_jager`), YAML docs, MotherDuck auth |
| **Data Pipelines** | [`jager-add-pipeline`](.agents/skills/jager-add-pipeline/SKILL.md) | dlt ingestion pipelines (OLAP, OLTP, Reverse ETL), FastAPI endpoints in dapp |
| **Database Ops** | [`jager-database-ops`](.agents/skills/jager-database-ops/SKILL.md) | Parallel database cloning (`clone-db.js`), schema migrations, MotherDuck manual imports |
| **n8n Workflows** | [`jager-n8n-workflow-ops`](.agents/skills/jager-n8n-workflow-ops/SKILL.md) | LinkedIn scheduling & dual-track publishing (individual vs Zernio), AI persona prompts |
| **Machine Learning** | [`jager-ml-pipeline`](.agents/skills/jager-ml-pipeline/SKILL.md) | 1 use case 1 subfolder rule, MotherDuck feature queries, prediction endpoints, tests |
| **Release & GitOps** | [`jager-release-and-deployment`](.agents/skills/jager-release-and-deployment/SKILL.md) | Tri-repo release flow (Jager, CDB, Jager-Deployment), GitOps self-hosted runner, secrets |
| **CDB Integration** | [`jager-cdb-integration`](.agents/skills/jager-cdb-integration/SKILL.md) | Architectural boundary, REST API authentication, MotherDuck OLAP sync (`ingest_cdb.py`), and port mappings |
| **Scripts Reference** | [`scripts/README.md`](scripts/README.md) | Overview of local developer scripts |
| **DAPP control plane** | [`src/dapp/README.md`](src/dapp/README.md) (pointer) + DAPP repo | Pipelines/ML live in DAPP; Jager n8n calls HTTP |

---

## SDLC & Utility Scripts

These utility scripts keep your local environment synchronized with production schemas, data, and workflows:

### 1. Database Cloning (`clone-db.js`)

Clones production databases (`jager`, `n8n`) into your local Docker environment in parallel (with credentials automatically excluded for safety):

```bash
# 1. Automatic run using PROD_DATABASE_URL from .env:
node scripts/clone-db.js

# 2. Or pass production connection URL explicitly:
node scripts/clone-db.js "postgresql://user:password@prod-host:5432/jager"

# 3. Common options:
node scripts/clone-db.js --skip-n8n          # Clone only the jager app database
node scripts/clone-db.js --include-history   # Include large n8n execution history tables
```

> [!TIP]
> For more CLI options and parallel worker flags, see the [Database Ops Skill](.agents/skills/jager-database-ops/SKILL.md).

### 2. Database Migrations & Seeding

```bash
# Creates schemas (s_*, t_*, m_*), migrates legacy public data, seeds defaults:
node scripts/migrate-db.js
```

### 3. Workflow Syncing & Management

```bash
# Check for differences between local JSON files and n8n database:
node scripts/compare-workflows.js

# Synchronize n8n database workflows back to local JSON files:
node scripts/sync-workflows.js
```

### 4. MotherDuck Manual Spreadsheet Ingestion

```bash
# Staging Mode (Default):
.venv/bin/python scripts/import_xlsx_motherduck.py

# Production Mode:
.venv/bin/python scripts/import_xlsx_motherduck.py --prod
```

---

## Release Pipeline

We have established a manual trigger release CI pipeline via GitHub Actions.

### Triggering a Release

1. Navigate to the **Actions** tab in your GitHub repository.
2. Select the **Manual Release** workflow.
3. Click **Run workflow**, specify the version tag (e.g. `v1.0.0`), write release notes, and trigger the run.
4. The workflow will:
   - Validate that `src/n8n/workflows/workflow.json` is a valid JSON file.
   - Build the custom N8N Docker image to ensure compile-time correctness.
   - Create a GitHub Release with the specified tag and upload `workflow.json` as a release asset.
