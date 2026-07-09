# Jager 🚀

Jager is an AI-native leads generator, simplified to use **N8N** as the primary orchestration engine and component.

## Architecture

This repository has been streamlined to prioritize N8N workflows:
- **`src/n8n/`**: Contains the primary N8N configuration, including the custom `Dockerfile` and the workflow JSON.
- **`legacy/`**: Houses older backend, frontend, test files, and configurations kept for reference.

### Database Schema (ODS Namespaces)
We organize database tables into dedicated schemas following the `s_{{application_name}}` naming convention (with table prefixes removed):
- `s_reddit`: subreddits monitored, posts, and comments.
- `s_slack`: workspaces monitored, channels monitored, and messages.
- `s_substack`: feeds monitored and posts.
- `s_euro_stat`: regional GDP, crime rates, inflation, quarterly GDP, unemployment, HPI, and FX rates.
- `s_yahoo_finance`: stock index prices.
- `prediction` & `training`: prediction outputs and ML trained models.

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

### Cloning Production Database

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

---

## Workflow Syncing & Management

If you modify workflows in the N8N UI, or if you clone the production database and want to make sure your local JSON files are in sync with the database workflows (while preserving custom prompt integrations like reading markdown files), use the following utility scripts:

*   **Check for differences between database workflows and local JSON files:**
    ```bash
    node scripts/compare-workflows.js
    ```
*   **Synchronize database workflows back to local JSON files (merging and preserving custom prompt nodes):**
    ```bash
    node scripts/sync-workflows.js
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
