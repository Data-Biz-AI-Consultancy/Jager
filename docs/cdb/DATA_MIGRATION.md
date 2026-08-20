# CDB — Data Migration Plan

**Version**: 0.1 (Draft)
**Status**: Under Review
**Last Updated**: 2026-08-20

> This document defines the plan for migrating live data from Jager's `cdp` PostgreSQL database (port 5432, database `cdp`) into CDB's new `cdb` PostgreSQL database (port 5433, database `cdb`). It must be executed **before** Jager's n8n workflows are cut over to CDB endpoints.

---

## 1. Migration Overview

```
Jager PostgreSQL (port 5432)        CDB PostgreSQL (port 5433)
database: cdp                  →    database: cdb
schema: cdp                         schema: public
```

### Approach

A one-off Python migration script (`scripts/migrate_cdp_to_cdb.py`) reads from the Jager `cdp` database and writes to the CDB `cdb` database over the shared Docker network. It runs **outside** both services so it can be halted and re-run without side effects.

**Key design rules:**
- All writes are **upserts** (INSERT ... ON CONFLICT DO NOTHING) — safe to re-run
- Migrated records preserve original `created_at` and `updated_at` timestamps
- All new UUIDs are generated fresh in CDB (Jager's UUIDs are not reused — too risky given schema changes)
- A `jager_origin_id` is stored in `attributes` JSONB on migrated rows for traceability

---

## 2. Table-by-Table Mapping

### 2.1 `cdp.companies` → `companies`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `id` (UUID) | `attributes.jager_origin_id` | Not reused as PK |
| `company_name` | `name` | |
| `domain` | `domain` | Dedup key |
| `status` | *(dropped)* | Company lifecycle now tracked via Opportunities |
| `attributes` | `attributes` | Merged |
| `created_at` | `created_at` | Preserved |
| `updated_at` | `updated_at` | Preserved |
| — | `industry`, `size_range`, `city`, `country`, `avatar_url` | Defaulted to NULL |

**Deduplication**: If `domain` already exists in CDB, skip (ON CONFLICT DO NOTHING on `domain`).

---

### 2.2 `cdp.persons` → `persons`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `id` (UUID) | `attributes.jager_origin_id` | |
| `first_name` | `first_name` | |
| `last_name` | `last_name` | |
| `primary_email` | `primary_email` | |
| `primary_phone` | `primary_phone` | |
| `linkedin_url` | `linkedin_url` | Normalised via `normalise_linkedin_url()` |
| `city` | `city` | |
| `country` | `country` | |
| `status` | *(dropped)* | |
| `attributes` | `attributes` | Merged |
| `in_linkedin_connections` | `sources` | If TRUE, add `'linkedin'` to sources array |
| `in_substack_subscriber_export` | `sources` | If TRUE, add `'substack'` |
| `primary_company_id` | *(dropped)* | Recreated via PCR migration below |
| `person_segment_*`, `engagement_temperature`, `potential_opportunity_types` | *(dropped)* | Phase 4 |
| `created_at`, `updated_at` | preserved | |

**Deduplication**: ON CONFLICT on `primary_email` (if non-null) or `linkedin_url`.

---

### 2.3 `cdp.person_company_relationships` → `person_company_relationships`

Migrated after companies and persons are inserted (FKs available).

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `id` | `attributes.jager_origin_id` | |
| `person_id` | `person_id` | Looked up via `attributes.jager_origin_id` |
| `company_id` (or `client_account_id`) | `company_id` | Same lookup |
| `role` | `title` | |
| `is_current` | `is_current` | |
| `started_at`, `ended_at` | preserved | |

Also derive a PCR row from `cdp.persons.primary_company_id` where no PCR row exists for that person+company pair.

---

### 2.4 `cdp.activities` + `cdp.activities_notion_meeting_notes` → `activities` + `intake_notion_meeting_notes`

#### `cdp.activities` → `activities`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `id` | `attributes.jager_origin_id` | |
| `activity_type` | `type` | |
| `source` | `source` | |
| `source_id` | `source_id` | Dedup key |
| `person_id` | `person_id` | Via jager_origin_id lookup |
| `company_id` | `company_id` | |
| `title` | `title` | |
| `activity_date` | `occurred_at` | |
| `summary_or_content` | `summary` | |
| `participants` | `attributes.participants` | |
| `to_dos` | `attributes.to_dos` | |
| `url` | `attributes.url` | |

**Deduplication**: ON CONFLICT on `source_id`.

#### `cdp.activities_notion_meeting_notes` → `intake_notion_meeting_notes`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `page_id` | `page_id` | Dedup key |
| `title` | `title` | |
| `meeting_date` | — | maps to `intake_notion_meeting_notes.meeting_date` |
| `attendees` | `attendees` | |
| `summary_or_content` | `summary` | |
| `to_dos` | `to_dos` | |
| `url` | `url` | |
| `raw_payload` | `raw_payload` | |
| — | `status` | Set to `'resolved'` (already processed in Jager) |

---

### 2.5 `cdp.leads` + `cdp.leads_linkedin` + `cdp.leads_manual` → `leads` + `intake_linkedin_messages`

#### `cdp.leads` → `leads`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `id` | `source_ref_id` | Kept as reference |
| `person_id` | `person_id` | Via jager_origin_id lookup |
| `company_id` | `company_id` | |
| `status` | `stage` | Map: `prospect→new`, `contacted→contacted`, `qualified→qualified`, `closed→converted` or `disqualified` based on `signal_strength` |
| `source` | `source` | |
| `intent` | `intent` | |
| `signal_strength` | `signal_strength` | |
| `summary` | `notes` | |
| `created_at`, `updated_at` | preserved | |
| `message_count`, `convo_history`, `opportunity_type`, `rate` | `attributes.*` | Kept in JSONB |
| `lead_status_*`, `lead_stage_*` | *(dropped)* | |

**Stage mapping from Jager `status`:**
```
prospect            → new
reached             → contacted
decision_maker_reached → qualified
contract_signed     → converted
engaging            → qualified
completed           → converted
(anything else)     → new
```

#### `cdp.leads_linkedin` → `intake_linkedin_messages`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `conversation_id` | `conversation_id` | Dedup key |
| `full_name` | `participant_names` | |
| `message_count` | `raw_payload.message_count` | |
| `convo_history` | `raw_content` | |
| `raw_payload` | `raw_payload` | |
| — | `status` | Set to `'resolved'` |
| `person_id` | `resolved_person_id` | Via jager_origin_id lookup |

---

### 2.6 `cdp.persons_linkedins` → `intake_linkedin_connections`

| Jager column | CDB column | Notes |
|-------------|------------|-------|
| `connection_id` | `connection_id` | Dedup key |
| `first_name`, `last_name` | preserved | |
| `profile_url` | `profile_url` (mapped to `linkedin_url`) | Normalised |
| `email_address` | `email_address` | |
| `company`, `position` | `company`, `position` | |
| `connected_at` | `connected_at` | |
| `raw_payload` | `raw_payload` | |
| — | `status` | Set to `'resolved'` |
| *(via cdp.persons lookup)* | `resolved_person_id` | Look up person by `email_address` or `profile_url` match |

---

### 2.7 Tables NOT migrated

| Jager table | Reason |
|-------------|--------|
| `cdp.engagements` | Merged into `activities`; data already exists there |
| `cdp.persons_manual_substack` | Data already processed into `cdp.persons`; no separate intake needed |
| `cdp.person_segments` | Phase 4; not in CDB scope yet |
| `cdp.lead_statuses` | Replaced by `leads.stage` enum |

---

## 3. Migration Execution Order

Due to foreign key dependencies, tables must be migrated in this sequence:

```
1. companies
2. persons
3. person_company_relationships
4. intake_linkedin_connections
5. intake_linkedin_messages  (cdp.leads_linkedin)
6. intake_notion_meeting_notes  (cdp.activities_notion_meeting_notes)
7. activities  (cdp.activities)
8. leads  (cdp.leads)
```

---

## 4. Validation Queries

Run these against the CDB database after migration to confirm completeness:

```sql
-- Row count comparison (run equivalent on Jager side for comparison)
SELECT 'companies'                    AS tbl, COUNT(*) FROM companies
UNION ALL
SELECT 'persons',                             COUNT(*) FROM persons
UNION ALL
SELECT 'person_company_relationships',        COUNT(*) FROM person_company_relationships
UNION ALL
SELECT 'activities',                          COUNT(*) FROM activities
UNION ALL
SELECT 'leads',                               COUNT(*) FROM leads
UNION ALL
SELECT 'intake_linkedin_connections',         COUNT(*) FROM intake_linkedin_connections
UNION ALL
SELECT 'intake_linkedin_messages',            COUNT(*) FROM intake_linkedin_messages
UNION ALL
SELECT 'intake_notion_meeting_notes',         COUNT(*) FROM intake_notion_meeting_notes;

-- Orphaned FKs (should all return 0)
SELECT COUNT(*) FROM persons WHERE id NOT IN (SELECT person_id FROM person_company_relationships WHERE person_id IS NOT NULL)
  AND id NOT IN (SELECT person_id FROM activities WHERE person_id IS NOT NULL)
  AND id NOT IN (SELECT person_id FROM leads WHERE person_id IS NOT NULL);

-- Verify jager_origin_id traceability
SELECT COUNT(*) FROM persons WHERE attributes->>'jager_origin_id' IS NULL;
```

---

## 5. Rollback Plan

Since CDB is a **new, separate database**, rollback is trivial:
- Stop the migration script
- Drop and recreate the `cdb` database: `DROP DATABASE cdb; CREATE DATABASE cdb;`
- Re-run Alembic migrations to restore schema
- Re-run the migration script from the beginning (all writes are idempotent)

Jager's `cdp` database is **never modified** during migration — it's read-only from the migration script's perspective.

---

## 6. Cut-over Sequence

1. Run migration script → validate row counts
2. Manually spot-check 10 random persons in CDB UI vs Jager CDP UI
3. Update `CDB_API_URL` in Jager's `docker-compose.yml` from `http://cdp:8000` to `http://cdb-api:8000`
4. Update n8n workflow HTTP nodes (see [JAGER_INTEGRATION.md](JAGER_INTEGRATION.md))
5. Deploy updated Jager stack
6. Monitor n8n executions for 24h
7. If stable: deprecate Jager `cdp` service (do not delete yet — keep for 2 weeks)

---

*See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for CDB table definitions and [JAGER_INTEGRATION.md](JAGER_INTEGRATION.md) for the workflow cut-over steps.*
