import os
import sys
import dlt
import duckdb

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging

# Set up logging
logger = setup_logging("reverse-etl")

def run_reverse_etl():
    logger.info("Initializing Motherduck connection")
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    motherduck_database = os.getenv("MOTHERDUCK_DATABASE", "staging")

    if not motherduck_token:
        logger.error("MOTHERDUCK_TOKEN environment variable is not set")
        sys.exit(1)

    # Connect to Motherduck
    conn = duckdb.connect(f"md:{motherduck_database}?token={motherduck_token}")

    # Define the resources fetching from Motherduck
    @dlt.resource(name="fct_linkedin_personal_account_post_engagement", write_disposition="replace")
    def get_personal_engagement():
        logger.info("Fetching fct_linkedin_personal_account_post_engagement from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.fct_linkedin_personal_account_post_engagement")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(name="fct_linkedin_company_page_post_engagement", write_disposition="replace")
    def get_company_page_engagement():
        logger.info("Fetching fct_linkedin_company_page_post_engagement from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.fct_linkedin_company_page_post_engagement")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(name="timeslot_recommendations", write_disposition="replace")
    def get_timeslot_recommendations():
        logger.info("Fetching timeslot_recommendations from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.timeslot_recommendations")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(name="public_holidays", write_disposition="replace")
    def get_public_holidays():
        logger.info("Fetching public_holidays from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.public_holidays")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    # Set up DLT pipeline with PostgreSQL destination
    logger.info("Starting DLT pipeline with postgres destination")
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    
    postgres_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")

    pipeline = dlt.pipeline(
        pipeline_name="reverse_etl_motherduck",
        destination=dlt.destinations.postgres(credentials=postgres_url),
        dataset_name="s_motherduck"
    )

    # Run the pipeline
    try:
        load_info = pipeline.run([
            get_personal_engagement, 
            get_company_page_engagement,
            get_timeslot_recommendations,
            get_public_holidays
        ])
        logger.info(f"Reverse ETL completed successfully:\n{load_info}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_reverse_etl()
