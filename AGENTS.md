# Agent Rules & Conventions

## dbt Naming & Coding Conventions

### Model Configuration
- For all dbt models, config blocks must explicitly define the `materialized`, `schema`, and `alias` parameters.
- The `alias` always uses a shorter prefix matching the layer (`stg_`, `int_`, `fct_`), while the file name uses the full layer prefix (`staging__`, `intermediate__`, `marts__`).


### Staging Models
- For all staging models in the dbt project (located under `dbt/models/staging/`), the SQL file name must always be prefixed with the target schema name followed by a double underscore (e.g., `staging__<source_name>__<table_name>.sql`).
- References to these models in downstream models (intermediate, marts) must use this fully prefixed name.
- Staging models are strictly 1:1 atomic models mapped to a single ODS source table. **Never use JOINs in staging models.** Any logic requiring a JOIN must be promoted to an intermediate model.

### Intermediate Models
- For all intermediate models in the dbt project (located under `dbt/models/intermediate/`), the SQL file name must always be prefixed with `intermediate__` followed by the domain and a double underscore (e.g., `intermediate__<domain>__<model_name>.sql`).
- The `alias` in the config block uses the shorter `int_` prefix (e.g., `alias='int_buffer__linkedin_posts'`), while the file name uses the `intermediate__` prefix.
- References to these models in downstream models (marts) must use the fully prefixed name (e.g., `ref('intermediate__linkedin__post_engagement')`).

### Marts Models
- For all marts models in the dbt project (located under `dbt/models/marts/`), the SQL file name must always be prefixed with `marts__` followed by the domain and a double underscore (e.g., `marts__linkedin__company_page_post_engagement.sql`).
- The `alias` in the config block uses the `fct_` (or `dim_`) prefix (e.g., `alias='fct_linkedin_company_page_post_engagement'`), while the file name uses the `marts__` prefix.
- Marts models representing core business concepts or shared dimensions should be named in an application-agnostic manner without the application name prefix (e.g., use `marts__countries.sql` with alias `dim_countries` instead of `marts__nager__countries.sql` with alias `dim_nager__countries`).



### SQL Coding Style (Table Aliasing)
- Do not use short aliases (e.g., `p.`, `c.`, `a.`, `l.`, `b.`) in SQL queries.
- Always use full descriptive aliases (e.g., `posts.`, `channels.`, `analytics.`, `likes.`, `comments.`, `buffer_posts.`) for readability.

## Database Initialization and Migrations
- Whenever `src/db/init-user-db.sh` is changed, the database migration script `scripts/migrate-db.js` must be updated to match the changes and keep schemas/tables in sync.

## Documentation Integrity
- Always keep project README files (e.g. `README.md` at all levels) up to date when folders, scripts, configurations, or workflow files are added, moved, or deleted.

## Machine Learning Service Conventions
- In `src/ml`, organize ML scripts and pipelines inside subfolders based on use case (1 use case, 1 subfolder rule). Avoid placing use-case-specific files directly in the root of `src/ml`.

## Data Source Naming Conventions
- Always use the specific data source application name to name files, directories, database schemas/datasets, and endpoints representing that data source (e.g., use `nager` instead of generic `holiday`).





