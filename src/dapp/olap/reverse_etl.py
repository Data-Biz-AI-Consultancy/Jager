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

    @dlt.resource(name="sum_content_marketing_daily_performance", write_disposition="replace")
    def get_sum_content_marketing_daily_performance():
        logger.info("Fetching sum_content_marketing_daily_performance from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.sum_content_marketing_daily_performance")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(
        name="cdp_companies",
        write_disposition="replace",
        columns={
            "company_id": {"data_type": "text"},
            "company_name": {"data_type": "text"},
            "domain": {"data_type": "text"},
            "status": {"data_type": "text"},
            "attributes": {"data_type": "text"},
            "created_at_berlin": {"data_type": "timestamp"},
            "updated_at_berlin": {"data_type": "timestamp"},
        }
    )
    def get_cdp_companies():
        logger.info("Fetching cdp_companies from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.cdp_companies")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(
        name="cdp_persons",
        write_disposition="replace",
        columns={
            "person_id": {"data_type": "text"},
            "first_name": {"data_type": "text"},
            "last_name": {"data_type": "text"},
            "full_name": {"data_type": "text"},
            "primary_email": {"data_type": "text"},
            "primary_phone": {"data_type": "text"},
            "linkedin_url": {"data_type": "text"},
            "city": {"data_type": "text"},
            "country": {"data_type": "text"},
            "primary_company_id": {"data_type": "text"},
            "primary_company_name": {"data_type": "text"},
            "status": {"data_type": "text"},
            "person_segment_id": {"data_type": "text"},
            "person_segment_name": {"data_type": "text"},
            "person_segment_slug": {"data_type": "text"},
            "engagement_temperature": {"data_type": "text"},
            "in_linkedin_connections": {"data_type": "bool"},
            "in_substack_subscriber_export": {"data_type": "bool"},
            "created_at_berlin": {"data_type": "timestamp"},
            "updated_at_berlin": {"data_type": "timestamp"},
        }
    )
    def get_cdp_persons():
        logger.info("Fetching cdp_persons from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.cdp_persons")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(
        name="cdp_activities",
        write_disposition="replace",
        columns={
            "activity_id": {"data_type": "text"},
            "activity_type": {"data_type": "text"},
            "source": {"data_type": "text"},
            "source_id": {"data_type": "text"},
            "person_id": {"data_type": "text"},
            "company_id": {"data_type": "text"},
            "title": {"data_type": "text"},
            "activity_date_berlin": {"data_type": "date"},
            "summary_or_content": {"data_type": "text"},
            "to_dos": {"data_type": "text"},
            "participants": {"data_type": "text"},
            "url": {"data_type": "text"},
            "metadata": {"data_type": "text"},
            "created_at_berlin": {"data_type": "timestamp"},
            "updated_at_berlin": {"data_type": "timestamp"},
        }
    )
    def get_cdp_activities():
        logger.info("Fetching cdp_activities from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.cdp_activities")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(
        name="cdp_leads",
        write_disposition="replace",
        columns={
            "lead_id": {"data_type": "text"},
            "person_id": {"data_type": "text"},
            "company_id": {"data_type": "text"},
            "full_name": {"data_type": "text"},
            "description": {"data_type": "text"},
            "message_count": {"data_type": "bigint"},
            "summary": {"data_type": "text"},
            "convo_history": {"data_type": "text"},
            "intent": {"data_type": "text"},
            "signal_strength": {"data_type": "text"},
            "opportunity_type": {"data_type": "text"},
            "rate": {"data_type": "text"},
            "status": {"data_type": "text"},
            "source": {"data_type": "text"},
            "lead_status_id": {"data_type": "text"},
            "lead_status_name": {"data_type": "text"},
            "lead_status_slug": {"data_type": "text"},
            "lead_stage_slug": {"data_type": "text"},
            "lead_stage_name": {"data_type": "text"},
            "intake_at_berlin": {"data_type": "timestamp"},
            "updated_at_berlin": {"data_type": "timestamp"},
        }
    )
    def get_cdp_leads():
        logger.info("Fetching cdp_leads from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.cdp_leads")
        cols = [desc[0] for desc in res.description]
        for row in res.fetchall():
            yield dict(zip(cols, row))

    @dlt.resource(
        name="sum_cdp_weekly_network_digest",
        write_disposition="replace",
        columns={
            "date_berlin": {"data_type": "date"},
            "new_leads_count": {"data_type": "bigint"},
            "high_signal_leads_count": {"data_type": "bigint"},
            "active_pipeline_leads_count": {"data_type": "bigint"},
            "new_persons_count": {"data_type": "bigint"},
            "new_linkedin_connections_count": {"data_type": "bigint"},
            "new_substack_subscribers_count": {"data_type": "bigint"},
            "daily_activities_count": {"data_type": "bigint"},
            "total_leads_cumulative": {"data_type": "bigint"},
            "total_persons_cumulative": {"data_type": "bigint"},
            "total_companies_cumulative": {"data_type": "bigint"},
            "total_activities_cumulative": {"data_type": "bigint"},
            "high_priority_leads": {"data_type": "text"},
            "daily_activities_json": {"data_type": "text"},
            "calculated_at_berlin": {"data_type": "timestamp"},
        }
    )
    def get_sum_cdp_weekly_network_digest():
        logger.info("Fetching sum_cdp_weekly_network_digest from Motherduck")
        res = conn.execute("SELECT * FROM t_jager.sum_cdp_weekly_network_digest")
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
            get_public_holidays,
            get_sum_content_marketing_daily_performance,
            get_cdp_companies,
            get_cdp_persons,
            get_cdp_activities,
            get_cdp_leads,
            get_sum_cdp_weekly_network_digest
        ])
        logger.info(f"Reverse ETL completed successfully:\n{load_info}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_reverse_etl()
