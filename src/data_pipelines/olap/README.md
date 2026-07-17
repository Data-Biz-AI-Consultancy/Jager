# OLAP Ingestion & Transformations (MotherDuck)

This directory contains pipelines that load data from Postgres to the MotherDuck OLAP database for analytics, modeling, and reporting.

## MotherDuck ML Schemas

The ML service initializes and updates lightweight MotherDuck schemas for analytics and model workflows:

*   **`ds_features`**: Reusable feature tables and a small `feature_catalog` for discoverability. The first table is `linkedin_post_engagement_features`, which stores LinkedIn post time features such as `day_of_week`, `hour_of_day`, `is_weekend`, `is_business_hour`, and `hour_bucket`.
*   **`ds_training`**: Training snapshots, validation results, and serialized model registry entries.
*   **`ds_prediction`**: Model metadata and generated prediction outputs such as LinkedIn timeslot recommendations.

## Core Pipelines

*   **`ingest_buffer.py`**: Syncs `s_buffer.channels` and `s_buffer.posts` from the PostgreSQL OLTP database to the MotherDuck OLAP database staging catalog using DLT's native schema evolution and merge logic.
*   **`ingest_linkedin.py`**: Ingests raw LinkedIn exports and engagement metrics.
*   **`ingest_nager.py`**: Ingests public holiday records from the Nager.Date API.
*   **`ingest_substack.py`**: Ingests Substack article statistics and data.
*   **`ingest_zernio.py`**: Ingests analytics data from Zernio.
*   **`reverse_etl.py`**: Pushes analytics and processed recommendations back to the operational database.
