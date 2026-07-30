import os
import sys
import io
import csv
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


def get_gdrive_service():
    """Build Google Drive API client using service account credentials from env."""
    client_email = os.environ.get("GOOGLE_DRIVE__CREDENTIALS__CLIENT_EMAIL")
    private_key = os.environ.get("GOOGLE_DRIVE__CREDENTIALS__PRIVATE_KEY", "").replace("\\n", "\n")
    project_id = os.environ.get("GOOGLE_DRIVE__CREDENTIALS__PROJECT_ID")

    if not (client_email and private_key):
        logger.warning("Google Drive service account credentials not found in env. Falling back to mock data.")
        return None

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials_info = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": private_key,
            "client_email": client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        creds = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to initialize Google Drive API service: {e}. Falling back to mock data.")
        return None


@dlt.resource(
    name="substack_subscribers",
    write_disposition="merge",
    primary_key="id",
)
def fetch_google_drive_subscribers():
    """Resource to fetch Substack subscriber export CSV files from Google Drive.
    
    dlt automatically detects and evolves schema column types dynamically.
    """
    service = get_gdrive_service()
    if not service:
        logger.info("Yielding fallback seed Substack subscriber items...")
        for sub in get_mock_google_drive_subscribers():
            yield sub
        return

    try:
        from googleapiclient.http import MediaIoBaseDownload

        folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
        query = f"'{folder_id}' in parents and (mimeType = 'text/csv' or name contains '.csv') and trashed = false" if folder_id else "(mimeType = 'text/csv' or name contains '.csv') and trashed = false"

        logger.info(f"Searching Google Drive for CSV exports (query: {query})...")
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])

        if not files:
            logger.warning("No CSV export files found in Google Drive folder. Yielding fallback seeds.")
            for sub in get_mock_google_drive_subscribers():
                yield sub
            return

        for file in files:
            logger.info(f"Downloading Substack export CSV from Google Drive: {file['name']} ({file['id']})")
            request = service.files().get_media(fileId=file["id"])
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            fh.seek(0)
            content = fh.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))

            for row in reader:
                email = row.get("email") or row.get("Email Address") or row.get("Email")
                if not email:
                    continue
                
                email_clean = email.strip()
                sub_id = row.get("id") or row.get("User ID") or f"sub_{abs(hash(email_clean))}"
                now_iso = datetime.now(timezone.utc).isoformat()

                yield {
                    "id": str(sub_id),
                    "email": email_clean,
                    "first_name": row.get("first_name") or row.get("First Name") or "",
                    "last_name": row.get("last_name") or row.get("Last Name") or "",
                    "subscribed_at": row.get("created_at") or row.get("Subscribed At") or now_iso,
                    "subscription_type": row.get("type") or row.get("Subscription Type") or "free",
                    "company": row.get("company") or row.get("Company") or "",
                    "job_title": row.get("job_title") or row.get("Job Title") or "",
                    "phone": row.get("phone") or row.get("Phone Number") or "",
                    "linkedin_url": row.get("linkedin_url") or row.get("LinkedIn") or "",
                    "processed": 0,
                    "created_at": now_iso,
                }
    except Exception as e:
        logger.error(f"Error reading Google Drive files: {e}. Falling back to seed mock.")
        for sub in get_mock_google_drive_subscribers():
            yield sub


def run_ingestion():
    logger.info("Starting Google Drive Substack subscriber ingestion pipeline...")
    pipeline = create_postgres_pipeline(
        pipeline_name="google_drive_to_postgres",
        dataset_name="s_google_drive",
    )
    load_info = pipeline.run(fetch_google_drive_subscribers())
    logger.info(f"Pipeline execution completed: {load_info}")
    return load_info


if __name__ == "__main__":
    run_ingestion()
