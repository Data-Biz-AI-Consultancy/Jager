# Substack Data Ingestion

This workflow ([data_ingestion_substack.json](file:///Users/jimmypang/AntigravityProjects/Jager/src/n8n/workflows/data_ingestion/data_ingestion_substack.json)) fetches posts from monitored Substack feeds, retrieves rich metadata and post analytics (comments, reactions, restacks) via the unofficial Substack API, and upserts them into `s_substack.posts`.

## API Reference
Refer to the unofficial API documentation at [Substack Explorer API Docs](https://www.substackexplorer.com/api-docs).

## How It Works

1. **Fetch & Parse RSS**: Downloads feed XMLs and parses post details (`id`, `title`, `url`, `published_at`).
2. **Fetch API Analytics**: Converts post web URLs (`/p/{slug}`) into JSON endpoints (`/api/v1/posts/{slug}`) to query metrics (views, comments, reactions, body HTML, podcast, etc.).
3. **Database Upsert**: Saves all rich metadata, contents, and analytics to PostgreSQL.
