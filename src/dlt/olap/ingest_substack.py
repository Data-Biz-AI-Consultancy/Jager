import os
import sys
import dlt
from sqlalchemy import text

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from olap.utils import setup_logging, get_db_engine, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-substack")

def run_ingestion():
    logger.info("Connecting to PostgreSQL database")
    engine = get_db_engine()

    # Define the resources
    @dlt.resource(name="feeds_monitored", write_disposition="merge", primary_key="id")
    def get_feeds():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, name, feed_url, active, created_at FROM s_substack.feeds_monitored"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="posts",
        write_disposition="merge",
        primary_key="id",
        columns={
            "reactions": {"data_type": "json"},
            "audio_items": {"data_type": "json"},
            "podcast_fields": {"data_type": "json"},
            "theme_variables": {"data_type": "json"},
            "comments": {"data_type": "json"},
            "inbox_item": {"data_type": "json"}
        }
    )
    def get_posts():
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT id, feed_id, feed_name, author, title, content, url, published_at, processed, "
                "subtitle, slug, canonical_url, audience, is_published, type, meter_type, "
                "teaser_post_eligible, wordcount, language, post_date, updated_at, reaction_count, "
                "reactions, comment_count, child_comment_count, restacks, cover_image, "
                "cover_image_is_square, cover_image_is_explicit, body_html, truncated_body_text, "
                "section_id, audio_items, podcast_fields, theme_variables, comments, inbox_item "
                "FROM s_substack.posts"
            ))
            for row in result:
                yield dict(row._mapping)

    logger.info("Starting DLT pipeline")
    pipeline = create_motherduck_pipeline(
        pipeline_name="substack_ingestion",
        dataset_name="s_substack",  # Target schema name
    )

    # Run the pipeline
    load_info = pipeline.run([get_feeds, get_posts])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
