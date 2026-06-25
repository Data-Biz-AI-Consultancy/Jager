# Jager Scripts

This directory contains utility scripts for managing the Jager database schemas, migrations, and database cloning from production environments.

## Scripts Overview

### 1. Database Cloning: `clone-db.js`

The [`clone-db.js`](../scripts/clone-db.js) script clones the production database (`jager` and/or `n8n`) to your local Docker-based PostgreSQL instance.

#### How It Works:
1. **Pre-checks**: Verifies the Docker Compose environment is available, starts the local database if it's stopped, and stops dependent application services (`n8n` and `ml`) to release active connections and lock-outs.
2. **Dumping**: Uses `pg_dump` with directory format (`-Fd`), multi-threading (`-j`), and zero compression (`-Z 0`) to extract production schemas.
   - Bypasses sensitive production data (e.g., skips tables like `credentials_entity` and `shared_credentials` in `n8n`).
   - Optionally excludes execution logs/history (`execution_entity` in `n8n`).
3. **Database Re-creation**: Terminates active connections to the local database, drops the database, and creates a clean replacement.
4. **Restore & Sanitization**: Restores the database structure and remaining data using `pg_restore` (multi-threaded). For the `n8n` database, it also runs post-migration sanitization to:
   - Deactivate all workflows (`active = false`).
   - Truncate any credentials remnants to ensure safety.
5. **Teardown**: Restarts the dependent application containers (`ml` and `n8n`).

#### Usage:
```bash
node scripts/clone-db.js <PROD_DATABASE_URL> [options]
```

**Options:**
- `--skip-n8n`, `--jager-only` : Only clone the `jager` database.
- `--skip-jager`, `--n8n-only` : Only clone the `jager` database.
- `-j`, `--jobs <number>` : Number of parallel dump/restore jobs (default: `4`).
- `--exclude-history` : Exclude massive tables like `execution_entity` from `n8n` clone.

**Example:**
```bash
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --skip-n8n --jobs 4 --exclude-history
```

---

### 2. Database Migrations: `migrate-db.js`

The [`migrate-db.js`](../scripts/migrate-db.js) script runs DDL commands to establish schemas and tables in the local `jager` database, migrates legacy data from the `public` schema, and seeds default entries.

#### How It Works:
1. **Database Connection**: Automatically locates the PostgreSQL connection details using the `DATABASE_URL` or `DB_APPLICATION_URL` environment variables, falling back to default docker-compose service configuration.
2. **Schema & Table Creation**: Creates distinct schemas for each content source and domain:
   - `s_reddit`, `s_slack`, `s_substack`, `s_meetup`, `s_euro_stat`, `s_yahoo_finance`, `s_wordpress`, `s_linkedin`, `s_analytics`, `s_notion` (Sources)
   - `prediction`, `training` (ML Modeling)
   - `t_content_generation` (Output Generation)
   - `m_staging`, `m_fact`, `m_episodic` (Data Staging & Memory Models)
3. **Legacy Migration**: If legacy tables exist in the `public` schema (e.g., `reddit_posts` instead of `s_reddit.posts`), the script:
   - Identifies overlapping columns between old and new tables.
   - Copies the rows to the new schema table on conflict doing nothing.
   - Updates serial sequences to match the maximum ID.
   - Drops the legacy `public` table.
4. **Data Seeding**: Seeds the database with default monitored subreddits, RSS feeds (Substack, WordPress), and system directives.

#### Usage:
```bash
node scripts/migrate-db.js
```
*(Commonly run during service startup or manual updates inside the application workspace)*
