# Database Scripts

This directory contains utility scripts to manage database migration and production data cloning for the local Jager development environment.

## Scripts Overview

- **[clone-db.js](file:///Users/jimmypang/AntigravityProjects/Jager/scripts/clone-db.js)**: Clones PostgreSQL databases from a production server to your local Docker-based development environment.
- **[migrate-db.js](file:///Users/jimmypang/AntigravityProjects/Jager/scripts/migrate-db.js)**: Runs migrations (DDL), transfers legacy data from the `public` schema to new schema-scoped tables, and seeds initial configuration data.

---

## 1. Database Cloning Script (`clone-db.js`)

This script copies production databases to your local development environment. By default, it looks for the production `jager` database URL, derives the production `n8n` database URL, runs dumps using `pg_dump`, drops/recreates local databases in Docker, restores the data, and runs post-clone sanitization.

### Prerequisites
- Docker and Docker Compose (either `docker compose` or `docker-compose`) must be installed and running.
- Must be executed from the project root directory.

### Usage
```bash
node scripts/clone-db.js <PROD_DATABASE_URL> [options]
```

### Options
- `--skip-n8n` or `--jager-only`: Clones only the `jager` database, skipping `n8n`.
- `--skip-jager` or `--n8n-only`: Clones only the `n8n` database, skipping `jager`.

### Examples
```bash
# Clone both databases using connection string
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager"

# Clone only the jager database
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --skip-n8n
```

### Post-Clone Sanitization
To prevent accidents in development, when the `n8n` database is cloned:
1. All workflows are deactivated (`UPDATE workflow_entity SET active = false`).
2. Production credentials are deleted (`TRUNCATE credentials_entity CASCADE`).
3. The local `n8n` Docker service is restarted to apply database updates.

---

## 2. Database Migration Script (`migrate-db.js`)

This script manages schema creation, legacy migrations, and seeding default configuration values for the application database. It connects to the target database using connection strings or details from `.env` variables (`DATABASE_URL`, `DB_APPLICATION_URL`, or individual `DB_APPLICATION_*` parameters).

### Schema Creation
The script ensures the following PostgreSQL schemas exist:
- `s_reddit`, `s_slack`, `s_substack`, `s_meetup`, `s_euro_stat`, `s_yahoo_finance`, `s_wordpress`, `s_linkedin`, `s_analytics`, `s_notion` (for service-specific monitoring/storing).
- `prediction`, `training` (for machine learning models and outputs).
- `t_content_generation` (for draft/publish tasks).
- `m_staging`, `m_fact`, `m_episodic` (for memory representation and fact extraction).

### Legacy Data Migration
If the script detects older tables in the default `public` schema (e.g., `reddit_subreddits_monitored`), it automatically:
1. Detects columns matching the new schema-scoped tables.
2. Copies all data from `public` to the new schema-scoped tables using `INSERT INTO ... SELECT ... ON CONFLICT DO NOTHING`.
3. Adjusts serial sequences accordingly.
4. Safely drops the legacy table in `public`.

### Default Seeding
Seeds configuration tables with default parameters, including:
- Standard target subreddits (e.g., `r/smallbusiness`, `r/saas`).
- Monitored Substack feeds.
- Monitored WordPress feeds.
- Default analytics directives.

### Usage
Make sure environment variables in your `.env` file are set up, then run:
```bash
node scripts/migrate-db.js
```
