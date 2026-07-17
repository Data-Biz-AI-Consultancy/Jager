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

## Python Testing Conventions
- All Python scripts in the codebase, including data pipelines (`src/data_pipelines/`) and machine learning components (`src/ml/`), must have corresponding automated unit tests.
- Python tests should be added to the `tests/` directory and run using `pytest` via `uv run pytest tests/`.
- Ensure tests verify key functionalities like database connections, data transformations, API query formats, and model predictions using mocks/patches where appropriate.

## dlt Pipeline Conventions
- All data ingestion pipelines use **dlt** (data load tool) to move data from PostgreSQL (ODS) into Motherduck (OLAP) or from Motherduck back into PostgreSQL (Reverse ETL).
- Always use `create_motherduck_pipeline()` from `src/data_pipelines/common/utils.py` when creating a Motherduck-destination pipeline. Do NOT inline the pipeline creation logic.
- The `dataset_name` passed to `create_motherduck_pipeline()` must match the source schema name in PostgreSQL (e.g., `s_linkedin`, `s_buffer`). This controls the target schema in Motherduck.
- Always set `os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"` before creating any dlt pipeline to prevent nested table generation.
- Use `write_disposition="merge"` with an explicit `primary_key` for all OLAP ingestion resources. Use `write_disposition="replace"` only for Reverse ETL resources.
- Each ingestion pipeline script must be self-contained with `if __name__ == "__main__": run_ingestion()` and must import from `common.utils` (not duplicate the utility logic).

## Reverse ETL Conventions
- The Reverse ETL pipeline (`src/data_pipelines/olap/reverse_etl.py`) reads from the `t_jager` schema in Motherduck and loads data back into PostgreSQL under the `s_motherduck` schema.
- Always use `dataset_name="s_motherduck"` for the Reverse ETL dlt pipeline destination.
- The Reverse ETL pipeline must always close the DuckDB connection in a `finally` block after the pipeline run.
- Reverse ETL resources expose the curated `t_jager` tables (e.g., `fct_linkedin_personal_account_post_engagement`, `timeslot_recommendations`) that n8n workflows consume via PostgreSQL.

## dbt `t_jager` Layer Conventions
- The `t_jager` layer (`dbt/models/t_jager/`) is a **presentation/application layer** that serves as the single source of truth for the n8n application. It mirrors selected marts and ML prediction tables into one schema.
- File names in this layer follow the pattern `t_jager__<domain>__<model_name>.sql` (e.g., `t_jager__ds_prediction__timeslot_recommends.sql`).
- Models in `t_jager` typically use `SELECT * FROM <source_schema>.<table>` — they are thin pass-through views/tables exposing marts or ML output.
- The `alias` in the config block for `t_jager` models does NOT use a `fct_` or `stg_` prefix; it uses a descriptive name directly (e.g., `alias='timeslot_recommendations'`).

## Data Pipeline FastAPI Service Conventions
- The data pipeline service (`src/data_pipelines/main.py`) exposes HTTP POST endpoints for triggering pipeline scripts via subprocess.
- Endpoint naming convention: `/run/<pipeline_name>` for OLAP pipelines (e.g., `/run/ingest_linkedin`) and `/run/oltp/<pipeline_name>` for OLTP pipelines (e.g., `/run/oltp/ingest_wordpress`).
- Every new ingestion script added under `olap/` or `oltp/` must have a corresponding FastAPI endpoint added to `main.py`.
- The service is deployed as the `data-pipeline` Docker service and accessed by n8n via `DATA_PIPELINE_URL`.

## Docker Compose & Environment Conventions
- The `MOTHERDUCK_DATABASE` environment variable defaults to `staging` in both `docker-compose.yml` and pipeline code. Never hardcode `production` as the default.
- The `n8n` service must declare all environment variables needed by n8n workflows. When adding a new external API or integration, add its credentials to the `n8n` service's `environment` block in `docker-compose.yml`.
- The `ml` and `data-pipeline` services share `DATABASE_URL`, `MOTHERDUCK_TOKEN`, and `MOTHERDUCK_DATABASE` environment variables. Keep these in sync across all service definitions.

## n8n Agent Persona Conventions
- All n8n AI agent persona definitions live in `src/n8n/agents/` as Markdown files (one file per agent).
- Each agent file must define: `Role`, `LLM` (model used), and a `Personality & Grounding` section.
- All agents must communicate **entirely in English** — the only Italian allowed is a single greeting word at the start and a single sign-off at the end.
- All agents must use actual Unicode emojis (e.g., 💡, 📊) rather than text-based emoji codes (e.g., `:sparkles:`).
- All agents must embed reference URLs as Slack hyperlinks using the `<url|Anchor Text>` format — never as plain-text URLs on separate lines.
- When adding or modifying agent personas, keep the agent file in `src/n8n/agents/` in sync with the corresponding system prompt used inside the n8n workflow JSON.

## Prompt File Conventions
- Standalone LLM prompts used by n8n workflows live in `prompts/` as Markdown files, named by their functional purpose (e.g., `intent_detection.md`, `draft_response.md`).
- Prompts must use `{{VARIABLE_NAME}}` (double curly braces) for all dynamic input placeholders — consistent with n8n's expression syntax.
- Prompts must specify their output format explicitly (e.g., "Output only the JSON block", "Do not wrap in JSON"). Never leave output format ambiguous.






