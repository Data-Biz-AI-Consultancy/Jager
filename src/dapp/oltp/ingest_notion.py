import os
import sys
import time
import requests
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import dlt
from sqlalchemy import text

load_dotenv()

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_db_engine, create_postgres_pipeline

# Set up logging
logger = setup_logging("ingest-notion")


def get_notion_headers():
    token = os.getenv("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }


def get_active_databases(engine):
    databases = []
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT database_id, name, COALESCE(type, 'database') AS type FROM s_notion.databases_monitored WHERE active = true"))
            for row in result:
                databases.append(dict(row._mapping))
    except Exception as e:
        logger.warning(f"Failed to query s_notion.databases_monitored: {e}. Falling back to default list.")

    if not databases:
        databases = [
            {"database_id": "b5ad53f72b0e45e3b481e25da2703fd8", "name": "Leadership & Management", "type": "database"},
            {"database_id": "1686e98d4ef8806da4e1c28268b7365e", "name": "Data Science - AIs", "type": "database"},
            {"database_id": "4cd9498f5b5c48c6864d57bd36f7f82d", "name": "Data Science", "type": "database"},
            {"database_id": "32fcdb5f301b4a9c94329dcadeffca15", "name": "data engineering", "type": "database"},
            {"database_id": "f0501c9ac3bf4f0ea8d06b7ed6e40a31", "name": "Data Governance", "type": "database"},
            {"database_id": "8fc4f5d17d6644eaa6b199f11cb3bf2b", "name": "Data Visualization & Reporting", "type": "database"},
            {"database_id": "40906fc76abd4951bd4b283c9717d320", "name": "Product Management", "type": "database"},
            {"database_id": "2bdfbb81d5c043d0a5fdd3028ad2504f", "name": "Product Analytics", "type": "database"},
            {"database_id": "1d362ecd225241c0ab3c0fe4d0ed3cda", "name": "Software Engineering", "type": "database"},
            {"database_id": "2d56e98d4ef8806ba96cca38539b67e1", "name": "Business", "type": "database"},
            {"database_id": "f34619396f3c4be8b96fa64211eb18d7", "name": "Career", "type": "database"},
            {"database_id": "3876e98d4ef8807eab9be1b0b029246c", "name": "Interview Meeting notes", "type": "meeting_notes"},
            {"database_id": "3876e98d4ef880a6a61ae99d8912694f", "name": "Meetups & Seminars", "type": "meeting_notes"},
            {"database_id": "3a36e98d4ef88084a1aec60052a3cb80", "name": "FaDi meeting notes", "type": "meeting_notes"}
        ]
    return databases


def format_uuid(raw_id: str) -> str:
    if not raw_id:
        return ""
    cleaned = raw_id.replace("-", "")
    if len(cleaned) == 32:
        return f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:]}"
    return raw_id


def fetch_page_blocks(page_id: str, headers: dict):
    blocks = []
    formatted_id = format_uuid(page_id)
    url = f"https://api.notion.com/v1/blocks/{formatted_id}/children"
    has_more = True
    params = {"page_size": 100}

    while has_more:
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code != 200:
                break
            data = res.json()
            results = data.get("results", [])
            blocks.extend(results)
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            if has_more and next_cursor:
                params["start_cursor"] = next_cursor
            else:
                has_more = False
        except Exception as e:
            logger.warning(f"Error fetching blocks for page {page_id}: {e}")
            break
    return blocks


def parse_page_data(page: dict, blocks: list, db_type: str, now_iso: str):
    page_id = page.get("id", "")
    props = page.get("properties", {})
    
    title = ""
    parsed_props = {}

    for key, prop in props.items():
        if not prop:
            continue
        ptype = prop.get("type")
        val = None
        if ptype == "title":
            title = "".join([t.get("plain_text", "") for t in prop.get("title", [])])
            val = title
        elif ptype == "rich_text":
            val = "".join([t.get("plain_text", "") for t in prop.get("rich_text", [])])
        elif ptype == "number":
            val = prop.get("number")
        elif ptype == "select":
            val = prop.get("select", {}).get("name") if prop.get("select") else None
        elif ptype == "multi_select":
            val = ", ".join([s.get("name", "") for s in prop.get("multi_select", [])])
        elif ptype == "date":
            val = prop.get("date", {}).get("start") if prop.get("date") else None
        elif ptype == "checkbox":
            val = prop.get("checkbox")
        elif ptype == "url":
            val = prop.get("url")
        elif ptype == "email":
            val = prop.get("email")
        elif ptype == "phone_number":
            val = prop.get("phone_number")
        elif ptype == "people":
            val = ", ".join([p.get("name") or p.get("id", "") for p in prop.get("people", [])])
        parsed_props[key] = val

    if not title:
        title = page.get("title") or page.get("name") or "Untitled"

    # Icon & Cover
    icon = ""
    page_icon = page.get("icon")
    if page_icon:
        icon = page_icon.get("emoji") or (page_icon.get("external", {}).get("url") if page_icon.get("external") else page_icon.get("file", {}).get("url", ""))

    cover_url = ""
    page_cover = page.get("cover")
    if page_cover:
        cover_url = page_cover.get("external", {}).get("url") if page_cover.get("external") else page_cover.get("file", {}).get("url", "")

    url = page.get("url", "")
    created_time = page.get("created_time", now_iso)
    last_edited_time = page.get("last_edited_time", now_iso)

    # Block content extraction
    text_content = ""
    to_dos = []

    for b in blocks:
        btype = b.get("type")
        bcontent = b.get(btype, {})
        if not bcontent:
            continue

        btext = ""
        if "rich_text" in bcontent:
            btext = "".join([t.get("plain_text", "") for t in bcontent.get("rich_text", [])])
        elif btype == "child_page":
            btext = f"[Subpage: {bcontent.get('title', '')}]"
        elif btype == "child_database":
            btext = f"[Database: {bcontent.get('title', '')}]"

        if btype == "to_do":
            checked_str = "[x]" if bcontent.get("checked") else "[ ]"
            todo_line = f"{checked_str} {btext}"
            to_dos.append(todo_line)
            text_content += todo_line + "\n"
        elif btype == "code":
            lang = bcontent.get("language", "")
            text_content += f"```{lang}\n{btext}\n```\n"
        elif btext:
            if btype.startswith("heading_"):
                text_content += f"\n### {btext}\n"
            elif btype == "bulleted_list_item":
                text_content += f"* {btext}\n"
            elif btype == "numbered_list_item":
                text_content += f"1. {btext}\n"
            elif btype == "quote":
                text_content += f"> {btext}\n"
            elif btype == "callout":
                text_content += f"💡 {btext}\n"
            else:
                text_content += btext + "\n"

    if not text_content.strip():
        text_content = json.dumps(parsed_props)

    # Extract meeting fields
    meeting_date = None
    attendees = ""
    summary = ""
    transcription = ""
    action_items = ""
    recording_url = ""

    for k, val in parsed_props.items():
        if not val:
            continue
        lk = k.lower()
        if "date" in lk and not meeting_date:
            meeting_date = val
        elif any(term in lk for term in ["attendee", "participant", "who", "people"]) and not attendees:
            attendees = str(val)
        elif any(term in lk for term in ["summary", "tldr", "overview"]) and not summary:
            summary = str(val)
        elif any(term in lk for term in ["transcript", "transcription"]) and not transcription:
            transcription = str(val)
        elif any(term in lk for term in ["action", "next step", "task"]) and not action_items:
            action_items = str(val)
        elif any(term in lk for term in ["recording", "video", "audio", "link"]) and not recording_url:
            recording_url = str(val)

    if not meeting_date:
        meeting_date = created_time
    if not transcription:
        transcription = text_content
    if not summary:
        summary = text_content[:500]
    if not action_items and to_dos:
        action_items = "\n".join(to_dos)

    return {
        "id": page_id,
        "database_id": (page.get("parent", {}).get("database_id") or "").replace("-", ""),
        "database_type": db_type,
        "title": title,
        "content": text_content,
        "properties": parsed_props,
        "icon": icon,
        "cover_url": cover_url,
        "url": url,
        "created_time": created_time,
        "last_edited_time": last_edited_time,
        "meeting_date": meeting_date,
        "attendees": attendees,
        "summary": summary,
        "transcription": transcription,
        "action_items": action_items,
        "recording_url": recording_url,
        "processed": 0
    }


def run_ingestion(target_database_id=None, full_ingestion=False):
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    pipeline_start_time = time.time()
    logger.info("Starting Notion Data Ingestion pipeline")
    logger.info("Initializing DB engine to query active Notion databases...")
    engine = get_db_engine()
    databases = get_active_databases(engine)
    
    if target_database_id:
        target_clean = target_database_id.replace("-", "")
        databases = [db for db in databases if db["database_id"].replace("-", "") == target_clean]
        logger.info(f"Targeting single Notion database: {target_database_id} ({len(databases)} match found)")

    headers = get_notion_headers()

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    if full_ingestion:
        start_date = None
        filter_msg = "full historical ingestion"
    else:
        start_date = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        filter_msg = f"last_edited_time >= {start_date} (90-day lookback)"

    logger.info(f"Discovered {len(databases)} monitored Notion databases to ingest ({filter_msg})")

    pages_list = []
    meeting_notes_list = []
    api_fetch_start = time.time()
    total_blocks_count = 0

    for db_index, db in enumerate(databases, 1):
        db_start_time = time.time()
        db_id = db["database_id"].replace("-", "")
        formatted_db_id = format_uuid(db_id)
        db_name = db["name"]
        db_type = db.get("type", "database")
        logger.info(f"[{db_index}/{len(databases)}] Processing database '{db_name}' ({formatted_db_id}) [type: {db_type}]...")

        query_url = f"https://api.notion.com/v1/databases/{formatted_db_id}/query"
        has_more = True
        query_body = {
            "page_size": 100
        }
        if start_date:
            query_body["filter"] = {
                "timestamp": "last_edited_time",
                "last_edited_time": {"on_or_after": start_date}
            }
        page_batch_num = 0
        db_items_count = 0

        while has_more:
            try:
                page_batch_num += 1
                res = requests.post(query_url, headers=headers, json=query_body, timeout=15)
                if res.status_code != 200:
                    if res.status_code == 404:
                        logger.warning(f"  Could not access database '{db_name}' ({formatted_db_id}) [Status 404]. Please ensure the Notion Integration connection has been added to this database in the Notion UI.")
                    else:
                        logger.error(f"  Failed to query database '{db_name}' ({formatted_db_id}): Status {res.status_code} - {res.text}")
                    break
                data = res.json()
                pages = data.get("results", [])
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor")
                logger.info(f"  [DB: '{db_name}'] Batch {page_batch_num}: retrieved {len(pages)} page headers from database '{db_name}' ({formatted_db_id}) [has_more={has_more}]")

                if has_more and next_cursor:
                    query_body["start_cursor"] = next_cursor
                else:
                    has_more = False

                for p_idx, page in enumerate(pages, 1):
                    page_id = page.get("id", "")
                    if not page_id:
                        continue
                    formatted_page_id = format_uuid(page_id)

                    b_start = time.time()
                    blocks = fetch_page_blocks(page_id, headers)
                    b_duration = time.time() - b_start
                    total_blocks_count += len(blocks)

                    item_data = parse_page_data(page, blocks, db_type, now_iso)
                    item_data["database_id"] = db_id
                    db_items_count += 1

                    page_title = item_data.get("title", "Untitled")
                    logger.info(
                        f"    [DB: '{db_name}'] Ingesting Page {p_idx}/{len(pages)}: '{page_title[:60]}' | Page ID: {formatted_page_id} | Blocks: {len(blocks)} (fetched in {b_duration:.2f}s)"
                    )

                    if db_type == "meeting_notes":
                        meeting_notes_list.append(item_data)
                    else:
                        pages_list.append(item_data)

            except Exception as ex:
                logger.error(f"  Error querying Notion database {db_id}: {ex}")
                break

        db_duration = time.time() - db_start_time
        logger.info(f"  --> Completed database '{db_name}': {db_items_count} items fetched in {db_duration:.2f}s")

    api_fetch_duration = time.time() - api_fetch_start
    logger.info(f"===> Notion API Phase Complete: {len(pages_list)} knowledge pages, {len(meeting_notes_list)} meeting notes, {total_blocks_count} total blocks in {api_fetch_duration:.2f}s")

    resources = []

    if pages_list:
        @dlt.resource(
            name="pages",
            write_disposition="merge",
            primary_key="id",
            columns={
                "id": {"data_type": "text"},
                "database_id": {"data_type": "text"},
                "title": {"data_type": "text"},
                "content": {"data_type": "text"},
                "cover_url": {"data_type": "text"},
                "icon": {"data_type": "text"},
                "url": {"data_type": "text"},
                "created_time": {"data_type": "timestamp"},
                "last_edited_time": {"data_type": "timestamp"},
                "processed": {"data_type": "bigint"}
            }
        )
        def fetch_pages():
            for p in pages_list:
                yield {
                    "id": p["id"],
                    "database_id": p["database_id"],
                    "title": p["title"],
                    "content": p["content"],
                    "cover_url": p["cover_url"],
                    "icon": p["icon"],
                    "url": p["url"],
                    "created_time": p["created_time"],
                    "last_edited_time": p["last_edited_time"],
                    "processed": 0
                }
        resources.append(fetch_pages())

    if meeting_notes_list:
        @dlt.resource(
            name="meeting_notes",
            write_disposition="merge",
            primary_key="id",
            columns={
                "id": {"data_type": "text"},
                "database_id": {"data_type": "text"},
                "title": {"data_type": "text"},
                "meeting_date": {"data_type": "timestamp"},
                "attendees": {"data_type": "text"},
                "summary": {"data_type": "text"},
                "transcription": {"data_type": "text"},
                "action_items": {"data_type": "text"},
                "recording_url": {"data_type": "text"},
                "url": {"data_type": "text"},
                "created_time": {"data_type": "timestamp"},
                "last_edited_time": {"data_type": "timestamp"},
                "processed": {"data_type": "bigint"}
            }
        )
        def fetch_meeting_notes():
            for m in meeting_notes_list:
                yield {
                    "id": m["id"],
                    "database_id": m["database_id"],
                    "title": m["title"],
                    "meeting_date": m["meeting_date"],
                    "attendees": m["attendees"],
                    "summary": m["summary"],
                    "transcription": m["transcription"],
                    "action_items": m["action_items"],
                    "recording_url": m["recording_url"],
                    "url": m["url"],
                    "created_time": m["created_time"],
                    "last_edited_time": m["last_edited_time"],
                    "processed": 0
                }
        resources.append(fetch_meeting_notes())

    if not resources:
        logger.warning("No Notion pages or meeting notes fetched to ingest.")
        return None

    logger.info("Starting dlt pipeline load phase into PostgreSQL schema 's_notion'...")
    dlt_start_time = time.time()

    # Pre-flight: drop the legacy 'properties' column from both tables if it exists.
    # 'properties' was always empty ({}) and caused persistent type-mismatch errors
    # with dlt's PostgreSQL staging (dlt stages json as text; postgres can't implicitly
    # cast text → jsonb). Dropping the column is idempotent and eliminates the issue.
    logger.info("Running pre-flight schema migration: dropping legacy 'properties' column if present...")
    migrate_sql_statements = [
        "ALTER TABLE s_notion.pages DROP COLUMN IF EXISTS properties;",
        "ALTER TABLE s_notion.meeting_notes DROP COLUMN IF EXISTS properties;",
    ]
    with engine.begin() as conn:
        for stmt in migrate_sql_statements:
            try:
                conn.execute(text(stmt))
            except Exception as migration_err:
                # Table may not exist yet on first run — that's fine
                logger.debug(f"Pre-flight migration skipped (table may not exist yet): {migration_err}")
    logger.info("Pre-flight schema migration complete.")

    # Drop stale dlt pipeline cache (cached SQL packages from prior failed runs).
    # pipeline.drop() only clears the local working directory/packages — it does NOT
    # drop destination tables. Without this, dlt re-uses stale SQL packages that were
    # built with the old column type, causing the type-mismatch error to persist.
    pipeline = create_postgres_pipeline(pipeline_name="ingest_notion", dataset_name="s_notion")
    try:
        pipeline.drop()
        logger.info("Cleared stale dlt pipeline cache (prior failed packages removed).")
    except Exception as drop_err:
        logger.warning(f"Could not drop dlt pipeline cache (non-fatal): {drop_err}")

    pipeline = create_postgres_pipeline(pipeline_name="ingest_notion", dataset_name="s_notion")
    info = pipeline.run(resources)

    dlt_duration = time.time() - dlt_start_time
    total_pipeline_duration = time.time() - pipeline_start_time

    logger.info(f"===> Notion Ingestion Pipeline Complete in {total_pipeline_duration:.2f}s (Notion API: {api_fetch_duration:.2f}s, dlt load: {dlt_duration:.2f}s): {info}")
    return info


if __name__ == "__main__":
    args = sys.argv[1:]
    is_full = "--full" in args or "full=true" in args
    db_id = next((a for a in args if a not in ("--full", "full=true")), None)
    run_ingestion(db_id, full_ingestion=is_full)
