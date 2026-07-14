import os
import sys
import dlt
from sqlalchemy import text

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from olap.utils import setup_logging, get_db_engine, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-buffer")

def run_ingestion():
    logger.info("Connecting to PostgreSQL database")
    engine = get_db_engine()

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

    logger.info("Starting DLT pipeline")
    pipeline = create_motherduck_pipeline(
        pipeline_name="buffer_ingestion_v3",
        dataset_name="s_buffer",  # Target schema name
    )

    # Run the pipeline
    load_info = pipeline.run([get_channels, get_posts])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
