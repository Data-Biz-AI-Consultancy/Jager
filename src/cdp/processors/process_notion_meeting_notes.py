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
                    id,
                    database_id,
                    title,
                    meeting_date,
                    attendees,
                    summary,
                    transcription,
                    action_items,
                    recording_url,
                    url,
                    created_time,
                    last_edited_time
                FROM s_notion.meeting_notes
            """)
        ).mappings().fetchall()

        logger.info(f"Found {len(notes)} meeting notes in s_notion.meeting_notes.")

        # Stage 1: Ingest raw notes into cdp.activities_notion_meeting_notes intake table
        for note in notes:
            page_id = note.get("id")
            if not page_id:
                continue

            attendees = note.get("attendees") or ""
            meeting_date = note.get("meeting_date") or note.get("created_time")
            summary_or_content = note.get("transcription") or note.get("summary") or ""
            action_items = note.get("action_items") or ""
            to_dos = [item.strip() for item in action_items.split("\n") if item.strip()] if action_items else []

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
                    "database_name": note.get("database_id"),
                    "title": note.get("title") or "Untitled Meeting Note",
                    "meeting_date": meeting_date,
                    "attendees": attendees,
                    "summary_or_content": summary_or_content,
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
                    company_id,
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
            company_id = row["company_id"]

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
                        company_id,
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
                        :company_id,
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
                        company_id = COALESCE(EXCLUDED.company_id, cdp.activities.company_id),
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
                    "company_id": company_id,
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

        # Trigger entity resolution into cdp.persons from meeting notes attendees
        from processors.entity_resolution import resolve_persons
        persons_resolved = resolve_persons(cdp_conn)

    return {
        "status": "success",
        "intake_processed": intake_processed,
        "activities_processed": activities_processed,
        "persons_resolved": persons_resolved
    }


if __name__ == "__main__":
    result = process_notion_meeting_notes()
    print(json.dumps(result, indent=2))
