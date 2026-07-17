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

Spin up the N8N instance along with the Postgres database:

```bash
docker-compose up --build -d
```

Access your local N8N instance at [http://localhost](http://localhost).

---

## Architecture

This repository is streamlined to prioritize N8N workflows, supported by containerized databases and custom backends:
- **`src/n8n/`**: Contains the primary N8N configuration, including the custom `Dockerfile` and the workflow JSON.

### Database Schema (ODS Namespaces)
We organize database tables into dedicated schemas following the `s_{{application_name}}` naming convention (with table prefixes removed):
- `s_reddit`: subreddits monitored, posts, and comments.
- `s_slack`: workspaces monitored, channels monitored, and messages.
- `s_substack`: feeds monitored and posts.
- `s_euro_stat`: regional GDP, crime rates, inflation, quarterly GDP, unemployment, HPI, and FX rates.
- `s_yahoo_finance`: stock index prices.
- `prediction` & `training`: prediction outputs and ML trained models.

### MotherDuck ML Schemas
The ML service also initializes lightweight MotherDuck schemas for analytics and model workflows:
- `ds_features`: reusable feature tables and a small `feature_catalog` for discoverability. The first table is `linkedin_post_engagement_features`, which stores LinkedIn post time features such as `day_of_week`, `hour_of_day`, `is_weekend`, `is_business_hour`, and `hour_bucket`.
- `ds_training`: training snapshots, validation results, and serialized model registry entries.
- `ds_prediction`: model metadata and generated prediction outputs such as LinkedIn timeslot recommendations.

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
│   ├── data_pipelines/      # Ingestion & transformation pipelines (dlt & dbt)
│   ├── db/                  # Database initialization scripts
│   ├── ml/                  # Machine learning backend (training & prediction pipelines)
│   └── n8n/                 # N8N configuration, workflow files, and sync scripts
└── tests/                   # Automated Node.js and Python unit test suites
```

Refer to the folder-level READMEs for detailed guides:
- [scripts/README.md](scripts/README.md)
- [src/data_pipelines/README.md](src/data_pipelines/README.md)
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
    > docker-compose up --build -d
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

