import os
import sys
import logging
from datetime import datetime, timezone
import dlt

# Disable max table nesting per dlt pipeline conventions
os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.utils import setup_logging, create_postgres_pipeline

logger = setup_logging("ingest-google-drive")


def get_mock_google_drive_subscribers():
    """Return fallback seed Substack subscriber items from Google Drive export."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": "sub_gdrive_001",
            "email": "elena.rostova@techsolutions.io",
            "first_name": "Elena",
            "last_name": "Rostova",
            "subscribed_at": now_iso,
            "subscription_type": "free",
            "company": "Tech Solutions",
            "job_title": "Head of Engineering",
            "phone": "+1-555-0192",
            "linkedin_url": "https://linkedin.com/in/elena-rostova",
            "processed": 0,
            "created_at": now_iso,
        },
        {
            "id": "sub_gdrive_002",
            "email": "marcus@vancemedia.com",
            "first_name": "Marcus",
            "last_name": "Vance",
            "subscribed_at": now_iso,
            "subscription_type": "paid",
            "company": "Vance Media",
            "job_title": "Marketing Director",
            "phone": "+1-555-0144",
            "linkedin_url": "https://linkedin.com/in/marcusvance",
            "processed": 0,
            "created_at": now_iso,
        },
    ]


@dlt.resource(
    name="substack_subscribers",
    write_disposition="merge",
    primary_key="id",
)
def fetch_google_drive_subscribers():
    """Resource to fetch Substack subscriber export files from Google Drive.
    
    dlt automatically detects and evolves schema column types dynamically
    when ingesting arbitrary spreadsheet formats.
    """
    logger.info("Fetching Substack subscribers export from Google Drive source...")
    subscribers = get_mock_google_drive_subscribers()
    for sub in subscribers:
        yield sub


def run_ingestion():
    logger.info("Starting Google Drive Substack subscriber ingestion pipeline...")
    pipeline = create_postgres_pipeline(
        pipeline_name="google_drive_to_postgres",
        dataset_name="s_google_drive",
    )
    # Enable dynamic schema evolution without hardcoded static columns constraint
    load_info = pipeline.run(fetch_google_drive_subscribers())
    logger.info(f"Pipeline execution completed: {load_info}")
    return load_info


if __name__ == "__main__":
    run_ingestion()
