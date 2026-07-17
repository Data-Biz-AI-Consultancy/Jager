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

## Database Naming & Schema Conventions

### PostgreSQL Table Naming & Casing
- Use lowercase snake_case for all table names and column names.
- Use plural names for entity collections (e.g., `reddit_posts`, `substack_posts`, `slack_messages`, `yahoo_finance_stock_prices`).
- Tables storing data ingested from external APIs, connectors, or services MUST use the name of the connector or data source in snake_case as a prefix (e.g. `yahoo_finance_`), followed by a suffix representing the specific entity.
  - Example: Stock/Index price data ingested from Yahoo Finance must be saved in the `yahoo_finance_stock_prices` table.
  - Example: FX Rates data ingested from Eurostat must be saved in the `eurostat_fx_rates` table.

### Schema consistency & Migrations
- Whenever `src/db/init-user-db.sh` is changed, the database migration script `scripts/migrate-db.js` must be updated to match the changes and keep schemas/tables in sync.
- Ensure table names and schemas are kept consistent across `scripts/migrate-db.js`, `src/db/init-user-db.sh`, and within n8n database integration nodes.

## Documentation Integrity
- Always keep project README files (e.g. `README.md` at all levels) up to date when folders, scripts, configurations, or workflow files are added, moved, or deleted.
- In markdown files (like READMEs), always use relative paths for file links instead of absolute paths (e.g., use `[Scripts](scripts/README.md)` instead of `[Scripts](file:///path/to/scripts/README.md)`).

## Machine Learning Service Conventions
- In `src/ml`, organize ML scripts and pipelines inside subfolders based on use case (1 use case, 1 subfolder rule). Avoid placing use-case-specific files directly in the root of `src/ml`.

## Data Source Naming Conventions
- Always use the specific data source application name to name files, directories, database schemas/datasets, and endpoints representing that data source (e.g., use `nager` instead of generic `holiday`).

## Manual Data Ingestion to Motherduck
- For manual data ingestion scripts targeting Motherduck (e.g., uploading local spreadsheets), scripts must support both staging and production target databases using an environment flag (like `--prod`).
- By default, these scripts must target the staging database (`staging`) using `MOTHERDUCK_TOKEN` for safety.
- When `--prod` is passed, the script must switch to the production credentials/tokens (`MOTHERDUCK_TOKEN_PROD`) and database (`production` or custom variable).






