import os
import sys
import dlt
from sqlalchemy import text

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from olap.utils import setup_logging, get_db_engine, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-linkedin")

def run_ingestion():
    logger.info("Connecting to PostgreSQL database")
    engine = get_db_engine()

    # Define the resources
    @dlt.resource(name="ugc_posts", write_disposition="merge", primary_key="id")
    def get_ugc_posts():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, author, content, url, published_at, processed FROM s_linkedin.ugc_posts"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="social_action_likes", write_disposition="merge", primary_key="id")
    def get_social_action_likes():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, post_id, author, published_at, processed FROM s_linkedin.social_action_likes"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="social_action_comments", write_disposition="merge", primary_key="id")
    def get_social_action_comments():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, post_id, author, content, published_at, processed FROM s_linkedin.social_action_comments"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="all_comments", write_disposition="merge", primary_key="id")
    def get_all_comments():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, post_id, author, content, published_at, updated_at, processed FROM s_linkedin.all_comments"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="all_likes", write_disposition="merge", primary_key="id")
    def get_all_likes():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, post_id, author, published_at, updated_at, processed FROM s_linkedin.all_likes"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="invitations", write_disposition="merge", primary_key="id")
    def get_invitations():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, to_name, from_name, direction, inviter_profile_url, invitee_profile_url, message, sent_at, processed FROM s_linkedin.invitations"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="all_invitations", write_disposition="merge", primary_key="id")
    def get_all_invitations():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, to_name, from_name, direction, inviter_profile_url, invitee_profile_url, message, sent_at, updated_at, processed FROM s_linkedin.all_invitations"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="messages", write_disposition="merge", primary_key="id")
    def get_messages():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, conversation_id, sender_name, recipient_name, sender_profile_url, recipient_profile_urls, subject, content, folder, sent_at, processed FROM s_linkedin.messages"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="connections", write_disposition="merge", primary_key="id")
    def get_connections():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, first_name, last_name, profile_url, email_address, company, position, connected_at, updated_at, processed FROM s_linkedin.connections"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="following", write_disposition="merge", primary_key="id")
    def get_following():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, entity_name, profile_url, type, followed_at, updated_at, processed FROM s_linkedin.following"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="searches", write_disposition="merge", primary_key="id")
    def get_searches():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, query_text, searched_at, updated_at, processed FROM s_linkedin.searches"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="job_applications", write_disposition="merge", primary_key="id")
    def get_job_applications():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, company_name, job_title, application_date, status, job_url, updated_at, processed FROM s_linkedin.job_applications"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="job_seeker_preferences", write_disposition="merge", primary_key="id")
    def get_job_seeker_preferences():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, dream_companies, job_titles, locations, job_types, industries, company_sizes, activity_level, updated_at, processed FROM s_linkedin.job_seeker_preferences"))
            for row in result:
                yield dict(row._mapping)

    logger.info("Starting DLT pipeline")
    pipeline = create_motherduck_pipeline(
        pipeline_name="linkedin_ingestion",
        dataset_name="s_linkedin",  # Target schema name
    )

    # Run the pipeline
    load_info = pipeline.run([
        get_ugc_posts,
        get_social_action_likes,
        get_social_action_comments,
        get_all_comments,
        get_all_likes,
        get_invitations,
        get_all_invitations,
        get_messages,
        get_connections,
        get_following,
        get_searches,
        get_job_applications,
        get_job_seeker_preferences
    ])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
