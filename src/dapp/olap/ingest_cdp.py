import os
import sys
import dlt
from sqlalchemy import text

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_db_engine, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-cdp")


os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"

def run_ingestion():
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    logger.info("Connecting to PostgreSQL database")


    engine = get_db_engine(
        default_url="postgresql://jager:jager@db:5432/cdp",
        env_var="CDP_DATABASE_URL"
    )

    # Define the resources for core CDP entities
    @dlt.resource(
        name="activities",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "activity_type": {"data_type": "text"},
            "source": {"data_type": "text"},
            "source_id": {"data_type": "text"},
            "person_id": {"data_type": "text"},
            "company_id": {"data_type": "text"},
            "title": {"data_type": "text"},
            "activity_date": {"data_type": "timestamp"},
            "summary_or_content": {"data_type": "text"},
            "to_dos": {"data_type": "text"},
            "participants": {"data_type": "text"},
            "url": {"data_type": "text"},
            "metadata": {"data_type": "text"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
        }
    )
    def get_activities():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, activity_type, source, source_id, person_id, company_id, title, activity_date, summary_or_content, to_dos::text AS to_dos, participants, url, metadata::text AS metadata, created_at, updated_at FROM cdp.activities"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="companies",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "company_name": {"data_type": "text"},
            "domain": {"data_type": "text"},
            "status": {"data_type": "text"},
            "attributes": {"data_type": "text"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
        }
    )
    def get_companies():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, company_name, domain, status, attributes::text AS attributes, created_at, updated_at FROM cdp.companies"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="lead_statuses",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "slug": {"data_type": "text"},
            "name": {"data_type": "text"},
            "stage": {"data_type": "text"},
            "is_end_state": {"data_type": "bool"},
            "description": {"data_type": "text"},
            "criteria": {"data_type": "text"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
        }
    )
    def get_lead_statuses():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, slug, name, stage, is_end_state, description, criteria::text AS criteria, created_at, updated_at FROM cdp.lead_statuses"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="leads",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
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
            "raw_payload": {"data_type": "text"},
            "intake_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
            "lead_status_id": {"data_type": "text"},
            "lead_status_name": {"data_type": "text"},
            "lead_status_slug": {"data_type": "text"},
            "lead_stage_slug": {"data_type": "text"},
            "lead_stage_name": {"data_type": "text"},
        }
    )
    def get_leads():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, person_id, company_id, full_name, description, message_count, summary, convo_history, intent, signal_strength, opportunity_type, rate, status, source, raw_payload::text AS raw_payload, intake_at, updated_at, lead_status_id, lead_status_name, lead_status_slug, lead_stage_slug, lead_stage_name FROM cdp.leads"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="person_company_relationships",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "person_id": {"data_type": "text"},
            "company_id": {"data_type": "text"},
            "job_title": {"data_type": "text"},
            "department": {"data_type": "text"},
            "role_type": {"data_type": "text"},
            "is_primary": {"data_type": "bool"},
            "start_date": {"data_type": "date"},
            "end_date": {"data_type": "date"},
            "status": {"data_type": "text"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
        }
    )
    def get_person_company_relationships():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, person_id, company_id, job_title, department, role_type, is_primary, start_date, end_date, status, created_at, updated_at FROM cdp.person_company_relationships"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="person_segments",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "slug": {"data_type": "text"},
            "name": {"data_type": "text"},
            "description": {"data_type": "text"},
            "segment_type": {"data_type": "text"},
            "potential_opportunity_types": {"data_type": "text"},
            "criteria": {"data_type": "text"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
        }
    )
    def get_person_segments():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, slug, name, description, segment_type, potential_opportunity_types, criteria::text AS criteria, created_at, updated_at FROM cdp.person_segments"))
            for row in result:
                yield dict(row._mapping)

    @dlt.resource(
        name="persons",
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "first_name": {"data_type": "text"},
            "last_name": {"data_type": "text"},
            "primary_email": {"data_type": "text"},
            "primary_phone": {"data_type": "text"},
            "linkedin_url": {"data_type": "text"},
            "city": {"data_type": "text"},
            "country": {"data_type": "text"},
            "primary_company_id": {"data_type": "text"},
            "status": {"data_type": "text"},
            "attributes": {"data_type": "text"},
            "created_at": {"data_type": "timestamp"},
            "updated_at": {"data_type": "timestamp"},
            "in_linkedin_connections": {"data_type": "bool"},
            "in_substack_subscriber_export": {"data_type": "bool"},
            "person_segment_id": {"data_type": "text"},
            "person_segment_name": {"data_type": "text"},
            "person_segment_slug": {"data_type": "text"},
            "potential_opportunity_types": {"data_type": "text"},
            "engagement_temperature": {"data_type": "text"},
        }
    )
    def get_persons():
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, first_name, last_name, primary_email, primary_phone, linkedin_url, city, country, primary_company_id, status, attributes::text AS attributes, created_at, updated_at, in_linkedin_connections, in_substack_subscriber_export, person_segment_id, person_segment_name, person_segment_slug, potential_opportunity_types, engagement_temperature FROM cdp.persons"))
            for row in result:
                yield dict(row._mapping)




    logger.info("Starting DLT pipeline")
    pipeline = create_motherduck_pipeline(
        pipeline_name="cdp_ingestion",
        dataset_name="s_cdp",
    )

    # Run the pipeline
    load_info = pipeline.run([
        get_activities,
        get_companies,
        get_lead_statuses,
        get_leads,
        get_person_company_relationships,
        get_person_segments,
        get_persons,
    ])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")


if __name__ == "__main__":
    run_ingestion()
