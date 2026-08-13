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

*   **App Stack** (n8n, CDP, Postgres, Caddy, Cloudflare Tunnel):
    ```bash
    docker-compose --profile app up --build -d
    ```
*   **Data Stack** (DAPP Data App Service [ETL & ML], Postgres):
    ```bash
    docker-compose --profile data up --build -d
    ```
*   **Core Stack** (Postgres DB, Caddy, Tunnel):
    ```bash
    docker-compose --profile core up --build -d
    ```
*   **All Services**:
    ```bash
    docker-compose --profile all up --build -d
    ```

> [!TIP]
> You can also set `COMPOSE_PROFILES=app` (or `all`, `data`, `core`) in your `.env` file to default to a specific profile when running `docker-compose up`.

Access your local N8N instance at [http://localhost](http://localhost).

---

## Architecture & Microservice Interactions

Jager is structured around three core application components:

```mermaid
flowchart TD
    N8N["N8N Orchestration (src/n8n/)<br/>Workflow Scheduler & Orchestrator"]
    
    subgraph DataServices["Python Microservices & Services"]
        CDP["CDP App (src/cdp/)<br/>Customer Data Platform Domain Service"]
        DAPP["DAPP App (src/data_pipelines/ & src/ml/)<br/>Data Pipelines & ML Prediction Service"]
    end
    
    subgraph Storage["Storage Layer"]
        PG[("PostgreSQL (db)<br/>OLTP Data & cdp.* Schema")]
        MD[("MotherDuck<br/>OLAP Data & ds_* Datasets")]
    end
    
    N8N -->|"HTTP POST /process/*"| CDP
    N8N -->|"HTTP POST /run/* & /predict"| DAPP
    
    CDP -->|"Normalize Persons, Accounts & Relationships"| PG
    DAPP -->|"Ingest / Transform"| PG
    DAPP -->|"Sync OLAP / ML Predictions"| MD
```

*   **N8N Orchestration (`src/n8n/`)**: Serves as the central job orchestrator (operating like an AI-native Airflow) to schedule, trigger, and coordinate automated workflows via HTTP endpoints.
*   **CDP App ([src/cdp/](src/cdp/README.md))**: A dedicated FastAPI domain microservice responsible for Customer Data Platform logic (managing `cdp.persons`, `cdp.companies`, `cdp.leads`, `cdp.person_account_relationships`, and `cdp.engagements`). N8N triggers CDP processing via HTTP requests (`CDP_SERVICE_URL`).
*   **DAPP App ([src/dapp/](src/dapp/README.md))**: A consolidated Data App service combining data ingestion (**dlt**), transformations (**dbt**), and machine learning training/predictions (**ml**). N8N triggers pipelines (`DATA_PIPELINE_URL`) and ML inference (`ML_SERVICE_URL`) on this service.

### Database & Storage Schemas

We organize our databases into clear operational (OLTP) and analytical (OLAP) processing schemas:
- **OLTP Schema (PostgreSQL)**: Stores operational source data (`s_*` schemas) and core CDP domain entities (`cdp.*` schema). Refer to the [CDP Documentation](src/cdp/README.md) and [OLTP Database Documentation](src/dapp/oltp/README.md) for details.
- **OLAP Schema (MotherDuck)**: Stores curated presentation data (`t_jager`), features, validation snapshots, and serialized model metrics for ML workflows. Refer to the [OLAP Database Documentation](src/dapp/olap/README.md) for details.


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
│   ├── cdp/                 # Customer Data Platform domain microservice
│   ├── dapp/                # Data App (Ingestion, dbt transformations, and ML microservice)
│   ├── db/                  # Database initialization scripts
│   └── n8n/                 # N8N configuration, workflow files, and sync scripts
└── tests/                   # Automated Node.js and Python unit test suites
```

Refer to the folder-level READMEs for detailed guides:
- [scripts/README.md](scripts/README.md)
- [src/cdp/README.md](src/cdp/README.md)
- [src/db/README.md](src/db/README.md)
- [src/dapp/README.md](src/dapp/README.md)
- [src/dapp/oltp/README.md](src/dapp/oltp/README.md)
- [src/dapp/olap/README.md](src/dapp/olap/README.md)
- [src/dapp/ml/README.md](src/dapp/ml/README.md)
- [tests/README.md](tests/README.md)


### Important Root Files

*   **`docker-compose.yml`**: Configures and runs all local service containers (`db`, `n8n`, `ml`, `data-pipeline`, `caddy`, and `tunnel`).
*   **`AGENTS.md`**: Contains agent rules, naming conventions, coding styles, and project constraints.
*   **`package.json` / `pnpm-lock.yaml`**: Node dependencies and configuration for utility and synchronization scripts.
*   **`.releaserc.json`**: Semantic release configuration.
*   **`.env`**: Local environment variables configuration.

---

## SDLC & Utility Scripts

These utility scripts support the full software development lifecycle (SDLC), keeping your local environment synchronized with production schemas, data, and workflows. For more details on scripts, refer to the [Scripts Documentation](scripts/README.md).

### 1. Database Cloning & Migrations

*   **Cloning Production Database**:
    To clone the production database to your local dev environment, ensure you have `PROD_DATABASE_URL` set in your `.env` file, then run:
    ```bash
    node scripts/clone-db.js
    ```
    Alternatively, you can pass the connection URL explicitly:
    ```bash
    node scripts/clone-db.js "postgresql://YOUR_PROD_USER:YOUR_PROD_PASSWORD@YOUR_PROD_HOST:5432/jager"
    ```
    > [!NOTE]
    > After cloning the database, you should rebuild and restart the Docker containers so that N8N and other services hook onto the new databases properly:
    > ```bash
    > docker-compose --profile app up --build -d
    > ```

*   **Running Migrations**:
    To run database schema creations, legacy migrations, or configuration seeding locally:
    ```bash
    node scripts/migrate-db.js
    ```

### 2. Workflow Syncing & Management

If you modify workflows in the N8N UI, or if you clone the production database and want to make sure your local JSON files are in sync with the database workflows (while preserving custom prompt integrations like reading markdown files), use:

*   **Check for differences between database workflows and local JSON files:**
    ```bash
    node scripts/compare-workflows.js
    ```
*   **Synchronize database workflows back to local JSON files (merging and preserving custom prompt nodes):**
    ```bash
    node scripts/sync-workflows.js
    ```

### 3. MotherDuck Manual Data Ingestion

To import manual LinkedIn spreadsheet exports (XLSX) from `data/linkedin/` into MotherDuck under the `s_manual` schema:

*   **Staging (Default)**:
    ```bash
    .venv/bin/python scripts/import_xlsx_motherduck.py
    ```
*   **Production**:
    ```bash
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

