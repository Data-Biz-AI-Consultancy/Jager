import json
import os
import sys
import urllib.parse
import urllib.request
import dlt

# ==============================================================================
# Ingest CDB Entities (formerly CDP) into MotherDuck OLAP (`s_cdp` schema)
# ------------------------------------------------------------------------------
# NOTE: This script ingests data directly from the standalone CDB REST API
# (http://cdb-api:8000/api/v1/...) via service authentication.
# The dataset name and filename are maintained as `cdp` / `s_cdp` to prevent breaking
# downstream MotherDuck schemas and dbt analytical models.
# ==============================================================================

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-cdp")

os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"


def fetch_cdb_api(endpoint: str, api_base: str, api_key: str):
    cursor = None
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        url = f"{api_base.rstrip('/')}/api/v1/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                records = data.get("data", [])
                for record in records:
                    yield record
                pagination = data.get("pagination", {})
                if pagination and pagination.get("has_more") and pagination.get("next_cursor"):
                    cursor = pagination["next_cursor"]
                else:
                    break
        except Exception as exc:
            logger.warning(f"Error fetching from CDB API endpoint '{endpoint}': {exc}")
            break


def run_ingestion():
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    api_base = os.getenv("CDB_SERVICE_URL", "http://cdb-api:8000")
    api_key = os.getenv("CDB_API_KEY", "development-api-key")

    logger.info(f"Connecting to CDB API at {api_base}")

    # Define the resources for core CDB entities
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
        for item in fetch_cdb_api("activities", api_base, api_key):
            meta = item.get("metadata") or {}
            yield {
                "id": str(item.get("id")),
                "activity_type": item.get("type"),
                "source": item.get("source"),
                "source_id": item.get("source_id"),
                "person_id": str(item.get("person_id")) if item.get("person_id") else None,
                "company_id": str(item.get("company_id")) if item.get("company_id") else None,
                "title": item.get("title"),
                "activity_date": item.get("occurred_at"),
                "summary_or_content": item.get("body"),
                "to_dos": json.dumps(meta.get("to_dos", [])) if isinstance(meta, dict) else "[]",
                "participants": meta.get("participants") if isinstance(meta, dict) else None,
                "url": meta.get("url") if isinstance(meta, dict) else None,
                "metadata": json.dumps(meta) if isinstance(meta, dict) else "{}",
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }

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
        for item in fetch_cdb_api("companies", api_base, api_key):
            attrs = item.get("attributes") or {}
            yield {
                "id": str(item.get("id")),
                "company_name": item.get("name"),
                "domain": item.get("domain"),
                "status": item.get("industry") or "active",
                "attributes": json.dumps(attrs) if isinstance(attrs, dict) else "{}",
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            }

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
        for item in fetch_cdb_api("leads", api_base, api_key):
            yield {
                "id": str(item.get("id")),
                "person_id": str(item.get("person_id")) if item.get("person_id") else None,
                "company_id": str(item.get("company_id")) if item.get("company_id") else None,
                "full_name": item.get("notes") or "",
                "description": item.get("notes"),
                "message_count": 0,
                "summary": None,
                "convo_history": None,
                "intent": item.get("intent"),
                "signal_strength": item.get("signal_strength"),
                "opportunity_type": None,
                "rate": None,
                "status": item.get("stage"),
                "source": item.get("source"),
                "raw_payload": "{}",
                "intake_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "lead_status_id": None,
                "lead_status_name": item.get("stage"),
                "lead_status_slug": item.get("stage"),
                "lead_stage_slug": item.get("stage"),
                "lead_stage_name": item.get("stage"),
            }

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
        for item in fetch_cdb_api("persons", api_base, api_key):
            attrs = item.get("attributes") or {}
            yield {
                "id": str(item.get("id")),
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "primary_email": item.get("primary_email"),
                "primary_phone": item.get("primary_phone"),
                "linkedin_url": item.get("linkedin_url"),
                "city": item.get("city"),
                "country": item.get("country"),
                "primary_company_id": None,
                "status": "active",
                "attributes": json.dumps(attrs) if isinstance(attrs, dict) else "{}",
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "in_linkedin_connections": False,
                "in_substack_subscriber_export": False,
                "person_segment_id": None,
                "person_segment_name": None,
                "person_segment_slug": None,
                "potential_opportunity_types": None,
                "engagement_temperature": "cold",
            }

    logger.info("Starting DLT pipeline")
    pipeline = create_motherduck_pipeline(
        pipeline_name="cdp_ingestion",
        dataset_name="s_cdp",
    )

    # Run the pipeline
    load_info = pipeline.run([
        get_activities,
        get_companies,
        get_leads,
        get_persons,
    ])
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")


if __name__ == "__main__":
    run_ingestion()

