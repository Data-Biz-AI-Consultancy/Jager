import os
import sys
import logging
import dlt
from dlt.destinations import motherduck
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest-buffer")

def run_ingestion():
    pg_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    motherduck_database = os.getenv("MOTHERDUCK_DATABASE", "staging")

    if not motherduck_token:
        logger.error("MOTHERDUCK_TOKEN environment variable is not set")
        sys.exit(1)

    # Set DLT configurations
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"

    logger.info(f"Connecting to PostgreSQL database")
    engine = create_engine(pg_url)

    # Define the resources
    @dlt.resource(name="channels", write_disposition="merge", primary_key="id")
    def get_channels():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, name, service, organization_id, active, created_at, updated_at FROM s_buffer.channels"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="posts",
        write_disposition="merge",
        primary_key="id",
        columns={
            "assets": {"data_type": "json"},
            "metrics": {"data_type": "json"}
        }
    )
    def get_posts():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, text, channel_id, due_at, status, assets, metrics, reactions, comments, shares, reposts, clicks, reach, impressions, views, engagement_rate, created_at, updated_at, processed FROM s_buffer.posts"))
            for row in result:
                row_dict = dict(row._mapping)
                if row_dict.get("engagement_rate") is not None:
                    row_dict["engagement_rate"] = float(row_dict["engagement_rate"])
                yield row_dict

    logger.info(f"Starting DLT pipeline")
    pipeline = dlt.pipeline(
        pipeline_name="buffer_ingestion_v3",
        destination=motherduck(
            credentials={
                "database": motherduck_database,
                "password": motherduck_token
            },
            loader_file_format="jsonl"
        ),
        dataset_name="s_buffer",  # Target schema name
    )

    # Run the pipeline
    load_info = pipeline.run([get_channels, get_posts])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
