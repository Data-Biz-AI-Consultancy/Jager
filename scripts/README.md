# Jager — Database & Operational Scripts

This directory contains utility scripts to manage database migration, production cloning, and manual MotherDuck data ingestion.

For full CLI options, parallel worker configurations, and safety features, refer to the [Database Operations Skill](../.agents/skills/jager-database-ops/SKILL.md).

---

## 📋 Available Utilities

| Script | Purpose | Quick Command |
|--------|---------|---------------|
| [`clone-db.js`](clone-db.js) | Parallel multi-threaded dump and restore from production to local Docker | `node scripts/clone-db.js <PROD_URL>` |
| [`src/db/migrate-db.js`](../src/db/migrate-db.js) | Creates schemas (`s_*`, `t_*`, `m_*`), migrates legacy `public` data, and seeds configs | `node src/db/migrate-db.js` |
| [`import_xlsx_motherduck.py`](import_xlsx_motherduck.py) | Ingests manual XLSX spreadsheets into MotherDuck `s_manual` schema | `.venv/bin/python scripts/import_xlsx_motherduck.py [--prod]` |
