# Database Scripts

This directory contains utility scripts to manage database migration and production data cloning for the local Jager development environment.

## Scripts Overview

- **[clone-db.js](file:///Users/jimmypang/AntigravityProjects/Jager/scripts/clone-db.js)**: Clones PostgreSQL databases from a production server to your local Docker-based development environment.
- **[migrate-db.js](file:///Users/jimmypang/AntigravityProjects/Jager/scripts/migrate-db.js)**: Runs migrations (DDL), transfers legacy data from the `public` schema to new schema-scoped tables, and seeds initial configuration data.

---

## 1. Database Cloning Script (`clone-db.js`)

This script copies production databases to your local development environment. It clones both the `jager` and `n8n` databases **in parallel** by default, using `pg_dump` in directory format (`-Fd`) with multi-threaded dump and restore (`-j N`).

### Prerequisites
- Docker and Docker Compose (either `docker compose` or `docker-compose`) must be installed and running.
- Must be executed from the project root directory.
- PostgreSQL 13+ is recommended (for `DROP DATABASE WITH (FORCE)`); older versions are supported via automatic fallback.

### Usage
```bash
node scripts/clone-db.js <PROD_DATABASE_URL> [options]
```

### Options

| Flag | Description |
|---|---|
| `--skip-n8n`, `--jager-only` | Clone only the `jager` database, skip `n8n` |
| `--skip-jager`, `--n8n-only` | Clone only the `n8n` database, skip `jager` |
| `--exclude-history` | Exclude n8n execution log table **data** (`execution_entity`, `execution_data`, `execution_metadata`). Schema is still restored. Significantly speeds up the clone when those tables are large. |
| `--jobs <N>` | Number of parallel pg_dump/pg_restore workers per database. Defaults to `floor(cpu_count / 2)`, min 2, max 8. |

### Examples
```bash
# Clone both databases in parallel (default)
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager"

# Clone only the jager database
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --skip-n8n

# Clone both, skip heavy n8n execution logs, use 4 parallel workers
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --exclude-history --jobs 4
```

### What It Does (Step by Step)
1. **Detects** `docker compose` or `docker-compose` automatically.
2. **Starts** the local `db` container if it is not running.
3. **Waits** for PostgreSQL to be ready using `pg_isready` (polls every 1s, 30s timeout).
4. **Dumps** each database in directory format (`-Fd`) with `-j N` parallel workers.
   - For `n8n`, optionally excludes execution log table data with `--exclude-history`.
5. **Drops** the local database using `DROP DATABASE WITH (FORCE)` (PG 13+) to atomically terminate connections and drop, with automatic fallback to `DROP DATABASE` for older versions.
6. **Recreates** and **restores** the database using `pg_restore -Fd -j N`.
7. **Sanitizes** the cloned `n8n` database:
   - Deactivates all workflows (`UPDATE workflow_entity SET active = false`).
   - Removes production credentials (`TRUNCATE credentials_entity CASCADE`).
8. **Restarts** the local `n8n` Docker container.

### Performance Notes
- Both `jager` and `n8n` clones run **in parallel** via `Promise.all`. Total wall time is `max(jager_time, n8n_time)` instead of the sum.
- Directory format (`-Fd`) combined with `-j N` workers leverages multiple CPU cores for both dump and restore, offering significant speedups on multi-core machines and larger databases.
- Log output is prefixed with `[jager]` / `[n8n]` tags so interleaved parallel output stays readable.

### Post-Clone Sanitization
To prevent accidents in development, when the `n8n` database is cloned:
1. All workflows are **deactivated** (`UPDATE workflow_entity SET active = false`).
2. Production credentials are **deleted** (`TRUNCATE credentials_entity CASCADE`).
3. The local `n8n` Docker service is **restarted** to apply database updates.

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
