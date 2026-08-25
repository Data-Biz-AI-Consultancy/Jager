# Database Schema & Setup

This directory contains the database setup and initialization scripts for the Jager PostgreSQL OLTP database (`jager`).

> [!NOTE]
> The Customer Data Platform / CRM domain has been extracted into the standalone [CDB](../cdb) project. The `jager` database houses the operational intake staging schemas (`s_*`) and internal task/content generation tables (`t_*`).

## Files and Folders in `src/db/`
- [init-user-db.sh](init-user-db.sh): PostgreSQL initialization script run automatically on Docker startup.
- [migrate-db.js](migrate-db.js): Database migration and DDL synchronization script.
- [sql/](sql/): Directory containing single-source-of-truth SQL DDL and seed files shared across `init-user-db.sh` and `migrate-db.js`.
  - `sql/oltp_schema.sql`: Jager OLTP database schema DDL (operational and staging schemas).
  - `sql/oltp_seeds.sql`: Jager OLTP database seed data.

