import os
import sys
import dlt
from sqlalchemy import text

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_db_engine, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-cdp")


def run_ingestion():
    logger.info("Connecting to PostgreSQL database")
    engine = get_db_engine(
        default_url="postgresql://jager:jager@db:5432/cdp",
        env_var="CDP_DATABASE_URL"
    )

    # Define the resources
    @dlt.resource(name="companies", write_disposition="merge", primary_key="id")
    def get_companies():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, company_name, domain, status, attributes, created_at, updated_at FROM cdp.companies"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="persons", write_disposition="merge", primary_key="id")
    def get_persons():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, first_name, last_name, primary_email, primary_phone, linkedin_url, city, country, primary_company_id, status, attributes, created_at, updated_at, in_linkedin_connections, in_substack_subscriber_export, person_segment_id, person_segment_name, person_segment_slug, potential_opportunity_types, engagement_temperature FROM cdp.persons"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="persons_linkedins", write_disposition="merge", primary_key="connection_id")
    def get_persons_linkedins():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT connection_id, first_name, last_name, profile_url, email_address, company, position, connected_at, raw_payload, intake_at, updated_at FROM cdp.persons_linkedins"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="persons_manual_substack", write_disposition="merge", primary_key="id")
    def get_persons_manual_substack():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, email, first_name, last_name, full_name, phone, linkedin_url, country, subscribed_at, source_table, raw_payload, intake_at, updated_at FROM cdp.persons_manual_substack"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="leads_linkedin", write_disposition="merge", primary_key="conversation_id")
    def get_leads_linkedin():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT conversation_id, person_id, full_name, description, message_count, summary, convo_history, intent, signal_strength, opportunity_type, status, raw_payload, intake_at, updated_at FROM cdp.leads_linkedin"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="leads_manual", write_disposition="merge", primary_key="id")
    def get_leads_manual():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, person_id, company_id, full_name, description, rate, status, source, raw_payload, intake_at, updated_at FROM cdp.leads_manual"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="leads", write_disposition="merge", primary_key="id")
    def get_leads():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, person_id, company_id, full_name, description, message_count, summary, convo_history, intent, signal_strength, opportunity_type, rate, status, source, raw_payload, intake_at, updated_at, lead_status_id, lead_status_name, lead_status_slug, lead_stage_slug, lead_stage_name FROM cdp.leads"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="person_company_relationships", write_disposition="merge", primary_key="id")
    def get_person_company_relationships():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, person_id, company_id, job_title, department, role_type, is_primary, start_date, end_date, status, created_at, updated_at FROM cdp.person_company_relationships"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="activities_notion_meeting_notes", write_disposition="merge", primary_key="page_id")
    def get_activities_notion_meeting_notes():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT page_id, person_id, company_id, database_name, title, meeting_date, attendees, summary_or_content, to_dos, url, raw_payload, intake_at, updated_at FROM cdp.activities_notion_meeting_notes"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="activities", write_disposition="merge", primary_key="id")
    def get_activities():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, activity_type, source, source_id, person_id, company_id, title, activity_date, summary_or_content, to_dos, participants, url, metadata, created_at, updated_at FROM cdp.activities"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="person_segments", write_disposition="merge", primary_key="id")
    def get_person_segments():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, slug, name, description, segment_type, potential_opportunity_types, criteria, created_at, updated_at FROM cdp.person_segments"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(name="lead_statuses", write_disposition="merge", primary_key="id")
    def get_lead_statuses():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, slug, name, stage, is_end_state, description, criteria, created_at, updated_at FROM cdp.lead_statuses"))
            for row in result:
                yield dict(row._mapping)

    logger.info("Starting DLT pipeline")
    pipeline = create_motherduck_pipeline(
        pipeline_name="cdp_ingestion",
        dataset_name="s_cdp",
    )

    # Run the pipeline
    load_info = pipeline.run([
        get_companies,
        get_persons,
        get_persons_linkedins,
        get_persons_manual_substack,
        get_leads_linkedin,
        get_leads_manual,
        get_leads,
        get_person_company_relationships,
        get_activities_notion_meeting_notes,
        get_activities,
        get_person_segments,
        get_lead_statuses,
    ])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")


if __name__ == "__main__":
    run_ingestion()
