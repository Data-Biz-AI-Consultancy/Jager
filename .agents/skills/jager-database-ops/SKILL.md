---
name: jager-database-ops
description: >-
  Use this skill for database operations in Jager: cloning production databases locally
  in parallel with `clone-db.js`, running schema migrations and legacy data transfers
  with `migrate-db.js`, and manual spreadsheet ingestion to MotherDuck via `import_xlsx_motherduck.py`.
---

# Jager Database Operations & Migration Runbook

---

## 1. Cloning Production Databases Locally (`clone-db.js`)

Script: [`scripts/clone-db.js`](../../scripts/clone-db.js)

Clones the `jager` and `n8n` production PostgreSQL databases **in parallel** into your local Docker PostgreSQL container using multi-threaded directory format dumps (`pg_dump -Fd -j N` / `pg_restore`).

### Key Usage & CLI Flags

```bash
# 1. Parallel clone of both databases (skips large n8n execution history by default)
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager"

# 2. Clone only the jager application database
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --skip-n8n

# 3. Clone only n8n workflows & configuration
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --n8n-only

# 4. Include full execution history tables (large tables)
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --include-history

# 5. Set custom parallel worker threads (default: cpu_count / 2)
node scripts/clone-db.js "postgres://user:password@prod-host:5432/jager" --jobs 4
```

### Safety & Credentials Guarantee
- **Credentials Protection**: `n8n.credentials_entity` data is **always excluded** during dumping. Production API keys are never cloned to local machines.
- **Connection Termination**: Uses atomic `DROP DATABASE WITH (FORCE)` (PostgreSQL 13+) to safely drop and recreate the local database before restoring.

---

## 2. Database Migrations & Seeding (`migrate-db.js`)

Script: [`src/db/migrate-db.js`](../../src/db/migrate-db.js)

Manages PostgreSQL schema creation, legacy table migrations from `public`, and configuration seeding.

### Schemas Managed
- **Sources (`s_*`)**: `s_reddit`, `s_slack`, `s_substack`, `s_meetup`, `s_euro_stat`, `s_yahoo_finance`, `s_wordpress`, `s_linkedin`, `s_analytics`, `s_notion`
- **Machine Learning**: `prediction`, `training`
- **Content & Output**: `t_content_generation`
- **Memory Subsystem**: `m_staging`, `m_fact`, `m_episodic`

### Running Migrations
```bash
node src/db/migrate-db.js
```

### Schema Consistency Rules
- When updating `src/db/init-user-db.sh`, always synchronize table definitions in `src/db/migrate-db.js`.
- Any legacy table in `public` is automatically migrated to the schema-scoped table with sequences adjusted.

---

## 3. MotherDuck Spreadsheet Ingestion (`import_xlsx_motherduck.py`)

Script: [`scripts/import_xlsx_motherduck.py`](../../scripts/import_xlsx_motherduck.py)

Ingests manual XLSX spreadsheets into MotherDuck OLAP under the `s_manual` schema.

```bash
# Staging Mode (Default — connects to MOTHERDUCK_TOKEN)
.venv/bin/python scripts/import_xlsx_motherduck.py

# Production Mode (Switches to MOTHERDUCK_TOKEN_PROD)
.venv/bin/python scripts/import_xlsx_motherduck.py --prod
```

Convention: Always default to `staging`. Only use `--prod` when explicitly deploying to production.
