# PostgreSQL Table Naming Convention Guidelines

When creating or modifying PostgreSQL tables in Jager, follow these naming conventions:

1. **Connector/Source Prefixing**: 
   - Tables storing data ingested from external APIs, connectors, or services MUST use the name of the connector or data source in snake_case as a prefix (e.g. `yahoo_finance_`), followed by a suffix representing the specific entity.
   - Example: Stock/Index price data ingested from Yahoo Finance must be saved in the `yahoo_finance_stock_prices` table.
   - Example: FX Rates data ingested from Eurostat must be saved in the `eurostat_fx_rates` table.

2. **Casing & Pluralization**:
   - Use lowercase snake_case for all table names and column names.
   - Use plural names for entity collections (e.g., `reddit_posts`, `substack_posts`, `slack_messages`, `yahoo_finance_stock_prices`).

3. **Schema Consistency**:
   - Ensure table names and schemas are kept consistent across `scripts/migrate-db.js`, `src/db/init-user-db.sh`, and within n8n database integration nodes.
