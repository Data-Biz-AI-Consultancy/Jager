# Agent Rules & Conventions

## dbt Naming & Coding Conventions

### Model Configuration
- For all dbt models, config blocks must explicitly define the `materialized`, `schema`, and `alias` parameters.
- For staging models, the `alias` should map to the database object name using the shorter `stg_` prefix (e.g. `alias='stg_zernio__linkedin_posts'`), while the file name uses the `staging__` prefix.

### Staging Models
- For all staging models in the dbt project (located under `dbt/models/staging/`), the SQL file name must always be prefixed with the target schema name followed by a double underscore (e.g., `staging__<source_name>__<table_name>.sql`).
- References to these models in downstream models (intermediate, marts) must use this fully prefixed name.
- Staging models are strictly 1:1 atomic models mapped to a single ODS source table. **Never use JOINs in staging models.** Any logic requiring a JOIN must be promoted to an intermediate model.

### Intermediate Models
- For all intermediate models in the dbt project (located under `dbt/models/intermediate/`), the SQL file name must always be prefixed with `intermediate__` followed by the domain and a double underscore (e.g., `intermediate__<domain>__<model_name>.sql`).
- The `alias` in the config block uses the shorter `int_` prefix (e.g., `alias='int_buffer__linkedin_posts'`), while the file name uses the `intermediate__` prefix.
- References to these models in downstream models (marts) must use the fully prefixed name (e.g., `ref('intermediate__linkedin__post_engagement')`).


### SQL Coding Style (Table Aliasing)
- Do not use short aliases (e.g., `p.`, `c.`, `a.`, `l.`, `b.`) in SQL queries.
- Always use full descriptive aliases (e.g., `posts.`, `channels.`, `analytics.`, `likes.`, `comments.`, `buffer_posts.`) for readability.

