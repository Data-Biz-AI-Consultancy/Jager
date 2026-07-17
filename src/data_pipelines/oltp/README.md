# OLTP Database Ingestion (PostgreSQL)

This directory contains ingestion pipelines that write raw data from external APIs and sources into the local OLTP Postgres database (`db`).

## Database Schema (ODS Namespaces)

We organize database tables into dedicated ODS schemas following the `s_{{application_name}}` naming convention (with table prefixes removed):

*   **`s_reddit`**: Monitored subreddits, posts, and comments.
*   **`s_slack`**: Monitored workspaces, monitored channels, and messages.
*   **`s_substack`**: Monitored feeds and posts.
*   **`s_euro_stat`**: Regional GDP, crime rates, inflation, quarterly GDP, unemployment, HPI, and FX rates.
*   **`s_yahoo_finance`**: Stock index prices.
*   **`prediction` & `training`**: Prediction outputs and machine learning trained models.

> [!WARNING]
> The `prediction` and `training` schemas in PostgreSQL are legacy. This functionality should be migrated to MotherDuck (`ds_prediction`, `ds_training`) and these schemas should be dropped as part of a future cleanup.



## Ingestion Pipelines

*   **`ingest_eurostat_fx.py`**: Ingests foreign exchange rates and economic indicators from Eurostat.
*   **`ingest_wordpress.py`**: Ingests posts and content from monitored WordPress sites.
*   **`ingest_yahoo_finance.py`**: Ingests historical stock index price data from Yahoo Finance.
