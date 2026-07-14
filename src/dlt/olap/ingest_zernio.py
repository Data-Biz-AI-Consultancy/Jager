import os
import sys
import logging
import dlt
from dlt.destinations import motherduck
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest-zernio")

def run_ingestion():
    pg_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    motherduck_database = os.getenv("MOTHERDUCK_DATABASE", "staging")

    if not motherduck_token:
        logger.error("MOTHERDUCK_TOKEN environment variable is not set")
        sys.exit(1)

    # Set DLT configurations
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"

    logger.info("Connecting to PostgreSQL database")
    engine = create_engine(pg_url)

    # Define the resources
    @dlt.resource(name="linkedin_posts", write_disposition="merge", primary_key="id")
    def get_linkedin_posts():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, content, url, published_at, fetched_at FROM s_zernio.linkedin_posts"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="linkedin_post_analytics", write_disposition="merge", primary_key="post_id")
    def get_linkedin_post_analytics():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT post_id, impressions, likes, comments, shares, clicks, saves, sends, fetched_at FROM s_zernio.linkedin_post_analytics"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="linkedin_account_analytics", write_disposition="merge", primary_key="account_id")
    def get_linkedin_account_analytics():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT account_id, platform, username, impressions, members_reached, reactions, comments, reshares, post_saves, post_sends, fetched_at FROM s_zernio.linkedin_account_analytics"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="linkedin_follower_stats_timeline", write_disposition="merge", primary_key=("account_id", "date"))
    def get_linkedin_follower_stats_timeline():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT account_id, date, followers_count, growth, growth_percentage, fetched_at FROM s_zernio.linkedin_follower_stats_timeline"))
            for row in result:
                row_dict = dict(row._mapping)
                if row_dict.get("growth_percentage") is not None:
                    row_dict["growth_percentage"] = float(row_dict["growth_percentage"])
                if row_dict.get("date") is not None:
                    row_dict["date"] = row_dict["date"].isoformat() if hasattr(row_dict["date"], "isoformat") else str(row_dict["date"])
                yield row_dict

    @dlt.resource(name="linkedin_post_timeline", write_disposition="merge", primary_key=("post_id", "date"))
    def get_linkedin_post_timeline():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT post_id, date, impressions, reach, likes, comments, shares, saves, clicks, views, fetched_at FROM s_zernio.linkedin_post_timeline"))
            for row in result:
                row_dict = dict(row._mapping)
                if row_dict.get("date") is not None:
                    row_dict["date"] = row_dict["date"].isoformat() if hasattr(row_dict["date"], "isoformat") else str(row_dict["date"])
                yield row_dict

    @dlt.resource(name="linkedin_content_decay", write_disposition="merge", primary_key=("platform", "bucket_order"))
    def get_linkedin_content_decay():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT platform, bucket_order, bucket_label, avg_pct_of_final, post_count, fetched_at FROM s_zernio.linkedin_content_decay"))
            for row in result:
                row_dict = dict(row._mapping)
                if row_dict.get("avg_pct_of_final") is not None:
                    row_dict["avg_pct_of_final"] = float(row_dict["avg_pct_of_final"])
                yield row_dict

    logger.info("Starting DLT pipeline")
    pipeline = dlt.pipeline(
        pipeline_name="zernio_ingestion",
        destination=motherduck(
            credentials={
                "database": motherduck_database,
                "password": motherduck_token
            },
            loader_file_format="jsonl"
        ),
        dataset_name="s_zernio",  # Target schema name
    )

    # Run the pipeline
    load_info = pipeline.run([
        get_linkedin_posts,
        get_linkedin_post_analytics,
        get_linkedin_account_analytics,
        get_linkedin_follower_stats_timeline,
        get_linkedin_post_timeline,
        get_linkedin_content_decay
    ])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
