---
name: jager-dbt-model
description: >-
  Use this skill when the user wants to add, modify, or debug a dbt model in
  the Jager repo — including staging, intermediate, marts, t_jager, t_reporting,
  or t_slack layers — or when managing YAML documentation files, tests, or
  MotherDuck execution conventions.
---

# Jager dbt Model Authoring Guide

All dbt models live under `src/dapp/dbt/models/`. Each layer has strict naming and
config conventions. **Read this skill fully before creating or modifying any dbt model.**

---

## Layer Overview & File Naming

| Layer | Directory | File prefix | Alias prefix | Materialization |
|-------|-----------|-------------|--------------|-----------------|
| Staging | `staging/` | `staging__<source>__<table>.sql` | `stg_<source>__<table>` | `table` (always) |
| Intermediate | `intermediate/` | `intermediate__<domain>__<model>.sql` | `int_<domain>__<model>` | typically `table` |
| Marts | `marts/` | `marts__<domain>__<model>.sql` | `fct_<domain>_<model>` or `dim_<model>` | `table` |
| Marts Summary | `marts/` | `marts__sum__<domain>__<model>.sql` | `sum_<domain>_<model>` | `table` |
| t_jager | `t_jager/` | `t_jager__<domain>__<model>.sql` | descriptive name (no prefix) | `table` |
| t_reporting | `t_reporting/` | `t_reporting__<domain>__<model>.sql` | descriptive name | `table` |
| t_slack | `t_slack/` | `t_slack__<domain>__<model>.sql` | descriptive name | `table` |

---

## Step 1 — Write the SQL Model

```sql
-- staging/linkedin/staging__linkedin__posts.sql
{{ config(
    materialized='table',
    schema='staging',
    alias='stg_linkedin__posts'
) }}

SELECT
    id,
    text,
    created_at,
    ...
FROM {{ source('s_linkedin', 'linkedin_posts') }}
```

**Rules**:
- Staging: 1:1 with source table. **No JOINs** in staging models.
- Single-table queries: do NOT alias the table; refer to columns directly.
- JOINs: use full descriptive aliases (`posts.`, `channels.`), never short ones (`p.`, `c.`).
- Marts: use `ref()` for all upstream models, never `source()` directly.

---

## Step 2 — Create the YAML Documentation File

One YAML file per model, stored in a `tests_and_config/` subfolder within the model's domain directory.
The YAML filename must **exactly match** the SQL filename (with `.yml`).

```yaml
# staging/linkedin/tests_and_config/staging__linkedin__posts.yml
version: 2

models:
  - name: staging__linkedin__posts
    description: "Cleaned LinkedIn post data from the s_linkedin.linkedin_posts source table."
    columns:
      - name: id
        description: "LinkedIn post unique identifier."
        tests:
          - unique
          - not_null
      - name: created_at
        description: "Post creation timestamp (UTC)."
```

**Do NOT** use a shared `_models.yml` to document multiple models.

---

## Step 3 — Timezone Handling

| Layer | Date/time columns |
|-------|-------------------|
| Marts | UTC only: `date_utc`, `calculated_at_utc` |
| t_jager, t_slack, t_reporting | Berlin only: `date_berlin`, `created_at_berlin` (drop UTC columns) |

Always use **daily granularity** as the standard time dimension for reporting models.

---

## Step 4 — Run the Model Against MotherDuck

**Never** trigger an interactive SSO prompt. Always export tokens from `.env`:

```bash
motherduck_token=$(grep -E '^MOTHERDUCK_TOKEN=' .env | head -1 | cut -d= -f2-) \
MOTHERDUCK_DATABASE=$(grep -E '^MOTHERDUCK_DATABASE=' .env | head -1 | cut -d= -f2-) \
.venv/bin/dbt run --select staging__linkedin__posts
```

To run a full domain:
```bash
... .venv/bin/dbt run --select staging/linkedin
```

To test:
```bash
... .venv/bin/dbt test --select staging__linkedin__posts
```

Default `MOTHERDUCK_DATABASE` is `staging`. Pass `MOTHERDUCK_DATABASE=production` only when explicitly promoting.

---

## Step 5 — Reference in Downstream Models

Use the **full prefixed name** in `ref()`:

```sql
-- intermediate model
SELECT * FROM {{ ref('staging__linkedin__posts') }}

-- marts model referencing intermediate
SELECT * FROM {{ ref('intermediate__linkedin__post_engagement') }}
```

---

## Step 6 — t_jager / Presentation Layer

`t_jager` models are thin pass-throughs for n8n consumption:

```sql
-- t_jager/t_jager__ds_prediction__timeslot_recommends.sql
{{ config(
    materialized='table',
    schema='t_jager',
    alias='timeslot_recommendations'
) }}

SELECT * FROM {{ ref('marts__sum__ds_prediction__timeslot_recommends') }}
```

Alias has **no** `fct_` / `stg_` prefix. Use a clean, application-friendly name.
After changing a `t_jager` model, the Reverse ETL pipeline must be re-run (see `jager-add-pipeline` skill).

---

## Key Reference Files

| File | Purpose |
|------|---------|
| [`src/dapp/dbt/`](../../src/dapp/dbt/) | dbt project root |
| [`src/dapp/dbt/models/staging/`](../../src/dapp/dbt/models/staging/) | Staging models |
| [`src/dapp/dbt/models/marts/`](../../src/dapp/dbt/models/marts/) | Marts & summary models |
| [`src/dapp/dbt/models/t_jager/`](../../src/dapp/dbt/models/t_jager/) | Application presentation layer |
| [`AGENTS.md`](../../AGENTS.md) | Full Jager coding conventions |
