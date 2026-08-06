import os
import sys
import json
from sqlalchemy import text

cdp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
for path in (cdp_dir, root_dir):
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from shared.db import setup_logging, get_db_engine
except ImportError:
    from utils import setup_logging, get_db_engine

logger = setup_logging("cdp-notion-meeting-notes-processor")


def process_notion_meeting_notes():
    """
    Ingests meeting notes from s_notion.meeting_notes (in jager DB) into cdp.activities_notion_meeting_notes (in cdp DB),
    and then populates the consolidated cdp.activities entity table.
    """
    logger.info("Starting processing of Notion meeting notes into cdp schema...")
    jager_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/jager", env_var="JAGER_DATABASE_URL")
    cdp_engine = get_db_engine(default_url="postgresql://jager:jager@db:5432/cdp", env_var="DATABASE_URL")

    intake_processed = 0
    activities_processed = 0

    with jager_engine.begin() as jager_conn, cdp_engine.begin() as cdp_conn:
        # Check if s_notion.meeting_notes exists
        table_check = jager_conn.execute(
            text("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 's_notion' AND table_name = 'meeting_notes'
            """)
        ).fetchone()

        if not table_check:
            logger.info("Table s_notion.meeting_notes does not exist in jager DB. Skipping intake.")
            return {"intake_processed": 0, "activities_processed": 0}

        # Fetch meeting notes from jager DB
        notes = jager_conn.execute(
            text("""
                SELECT 
                    page_id,
                    database_name,
                    title,
                    created_time,
                    last_edited_time,
                    properties,
                    icon,
                    cover_url,
                    url,
                    text_content,
                    to_dos,
                    fetched_at
                FROM s_notion.meeting_notes
            """)
        ).mappings().fetchall()

        logger.info(f"Found {len(notes)} meeting notes in s_notion.meeting_notes.")

        # Stage 1: Ingest raw notes into cdp.activities_notion_meeting_notes intake table
        for note in notes:
            page_id = note.get("page_id")
            if not page_id:
                continue

            properties = note.get("properties") or {}
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except Exception:
                    properties = {}

            # Extract attendees & date if present in properties or standard fields
            attendees = properties.get("Attendees") or properties.get("People") or properties.get("Participants") or ""
            meeting_date = note.get("created_time")
            date_prop = properties.get("Date") or properties.get("Meeting Date")
            if date_prop:
                meeting_date = date_prop

            to_dos = note.get("to_dos") or []
            if isinstance(to_dos, str):
                try:
                    to_dos = json.loads(to_dos)
                except Exception:
                    to_dos = []

            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.activities_notion_meeting_notes (
                        page_id,
                        database_name,
                        title,
                        meeting_date,
                        attendees,
                        summary_or_content,
                        to_dos,
                        url,
                        raw_payload,
                        intake_at,
                        updated_at
                    ) VALUES (
                        :page_id,
                        :database_name,
                        :title,
                        :meeting_date,
                        :attendees,
                        :summary_or_content,
                        :to_dos,
                        :url,
                        :raw_payload,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (page_id) DO UPDATE SET
                        database_name = EXCLUDED.database_name,
                        title = EXCLUDED.title,
                        meeting_date = EXCLUDED.meeting_date,
                        attendees = EXCLUDED.attendees,
                        summary_or_content = EXCLUDED.summary_or_content,
                        to_dos = EXCLUDED.to_dos,
                        url = EXCLUDED.url,
                        raw_payload = EXCLUDED.raw_payload,
                        updated_at = NOW();
                """),
                {
                    "page_id": page_id,
                    "database_name": note.get("database_name"),
                    "title": note.get("title") or "Untitled Meeting Note",
                    "meeting_date": meeting_date,
                    "attendees": str(attendees) if attendees else None,
                    "summary_or_content": note.get("text_content"),
                    "to_dos": json.dumps(to_dos),
                    "url": note.get("url"),
                    "raw_payload": json.dumps(dict(note), default=str)
                }
            )
            intake_processed += 1

        logger.info(f"Ingested {intake_processed} rows into cdp.activities_notion_meeting_notes.")

        # Stage 2: Populate cdp.activities entity table solely from cdp.activities_notion_meeting_notes
        intake_rows = cdp_conn.execute(
            text("""
                SELECT 
                    page_id,
                    person_id,
                    client_account_id,
                    database_name,
                    title,
                    meeting_date,
                    attendees,
                    summary_or_content,
                    to_dos,
                    url
                FROM cdp.activities_notion_meeting_notes
            """)
        ).mappings().fetchall()

        for row in intake_rows:
            page_id = row["page_id"]
            title = row["title"]
            meeting_date = row["meeting_date"]
            summary_or_content = row["summary_or_content"]
            to_dos = row["to_dos"]
            if isinstance(to_dos, str):
                try:
                    to_dos = json.loads(to_dos)
                except Exception:
                    to_dos = []
            participants = row["attendees"]
            url = row["url"]

            # Identity resolution attempt (optional lookup against persons/accounts)
            person_id = row["person_id"]
            client_account_id = row["client_account_id"]

            metadata = {
                "database_name": row["database_name"],
                "source_intake_table": "cdp.activities_notion_meeting_notes"
            }

            cdp_conn.execute(
                text("""
                    INSERT INTO cdp.activities (
                        activity_type,
                        source,
                        source_id,
                        person_id,
                        client_account_id,
                        title,
                        activity_date,
                        summary_or_content,
                        to_dos,
                        participants,
                        url,
                        metadata,
                        created_at,
                        updated_at
                    ) VALUES (
                        'meeting_note',
                        'notion_meeting_notes',
                        :source_id,
                        :person_id,
                        :client_account_id,
                        :title,
                        :activity_date,
                        :summary_or_content,
                        :to_dos,
                        :participants,
                        :url,
                        :metadata,
                        NOW(),
                        NOW()
                    )
                    ON CONFLICT (source_id) DO UPDATE SET
                        person_id = COALESCE(EXCLUDED.person_id, cdp.activities.person_id),
                        client_account_id = COALESCE(EXCLUDED.client_account_id, cdp.activities.client_account_id),
                        title = EXCLUDED.title,
                        activity_date = EXCLUDED.activity_date,
                        summary_or_content = EXCLUDED.summary_or_content,
                        to_dos = EXCLUDED.to_dos,
                        participants = EXCLUDED.participants,
                        url = EXCLUDED.url,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW();
                """),
                {
                    "source_id": page_id,
                    "person_id": person_id,
                    "client_account_id": client_account_id,
                    "title": title,
                    "activity_date": meeting_date,
                    "summary_or_content": summary_or_content,
                    "to_dos": json.dumps(to_dos),
                    "participants": participants,
                    "url": url,
                    "metadata": json.dumps(metadata)
                }
            )
            activities_processed += 1

        logger.info(f"Populated {activities_processed} records in cdp.activities.")

    return {
        "status": "success",
        "intake_processed": intake_processed,
        "activities_processed": activities_processed
    }


if __name__ == "__main__":
    result = process_notion_meeting_notes()
    print(json.dumps(result, indent=2))
