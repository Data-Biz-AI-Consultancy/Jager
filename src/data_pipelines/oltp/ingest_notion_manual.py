import os
import sys
import re
import requests
from datetime import datetime, timedelta, timezone
import dlt

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_db_engine, get_http_headers, create_postgres_pipeline

# Set up logging
logger = setup_logging("ingest-notion-manual")

MANUAL_PAGE_ID = os.getenv("NOTION_MANUAL_INGESTION_PAGE_ID", "3ad6e98d4ef8808e90e5d12894842709")


def get_notion_headers():
    token = os.getenv("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }


def format_uuid(raw_id: str) -> str:
    cleaned = raw_id.replace("-", "")
    if len(cleaned) == 32:
        return f"{cleaned[:8]}-{cleaned[8:12]}-{cleaned[12:16]}-{cleaned[16:20]}-{cleaned[20:]}"
    return raw_id


def to_snake_case(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_').lower()
    return s


def derive_table_name(prefix: str, entity_name: str) -> str:
    cleaned_prefix = to_snake_case(prefix)
    cleaned_entity = to_snake_case(entity_name)

    if cleaned_prefix:
        if cleaned_entity:
            if cleaned_entity.startswith(cleaned_prefix + "_"):
                return cleaned_entity
            return f"{cleaned_prefix}_{cleaned_entity}"
        return f"{cleaned_prefix}_pages"
    return cleaned_entity or "pages"


def discover_child_sources(parent_id: str, current_prefix: str = "", is_root: bool = True, visited=None):
    if visited is None:
        visited = set()

    formatted_id = format_uuid(parent_id)
    if formatted_id in visited:
        return [], []
    visited.add(formatted_id)

    databases = []
    subpages = []
    headers = get_notion_headers()
    url = f"https://api.notion.com/v1/blocks/{formatted_id}/children"

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            blocks = res.json().get("results", [])
            for b in blocks:
                btype = b.get("type")
                if btype == "child_database":
                    db_id = b.get("id", "").replace("-", "")
                    title = b.get("child_database", {}).get("title", "Manual Ingestion DB")
                    databases.append({
                        "id": db_id,
                        "name": title,
                        "prefix": current_prefix
                    })
                elif btype == "child_page":
                    page_id = b.get("id", "")
                    title = b.get("child_page", {}).get("title", "Manual Subpage")

                    # Direct child pages under MANUAL_PAGE_ID define the table prefix
                    child_prefix = to_snake_case(title) if is_root else current_prefix

                    subpages.append({
                        "id": page_id,
                        "title": title,
                        "parent_id": parent_id,
                        "prefix": child_prefix
                    })

                    # Recursively discover child sources under this subpage
                    child_dbs, child_pages = discover_child_sources(
                        page_id,
                        current_prefix=child_prefix,
                        is_root=False,
                        visited=visited
                    )
                    databases.extend(child_dbs)
                    subpages.extend(child_pages)
        else:
            logger.warning(f"Could not fetch children for block {formatted_id}: Status {res.status_code}")
    except Exception as e:
        logger.error(f"Error fetching child blocks for page {formatted_id}: {e}")

    return databases, subpages


def run_ingestion():
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    logger.info(f"Starting Notion Manual Data Ingestion for parent page {MANUAL_PAGE_ID}")

    headers = get_notion_headers()
    databases, subpages = discover_child_sources(MANUAL_PAGE_ID, is_root=True)

    # Fallback to Notion database search if no sources discovered
    if not databases and not subpages:
        try:
            search_res = requests.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json={"filter": {"value": "database", "property": "object"}},
                timeout=10
            )
            if search_res.status_code == 200:
                for db in search_res.json().get("results", []):
                    db_id = db.get("id", "").replace("-", "")
                    title = "".join([t.get("plain_text", "") for t in db.get("title", [])])
                    databases.append({"id": db_id, "name": title or "Manual Data Ingestion", "prefix": ""})
        except Exception as e:
            logger.error(f"Error searching Notion databases fallback: {e}")

    logger.info(f"Discovered {len(databases)} target databases and {len(subpages)} subpages under parent page")

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    @dlt.resource(
        name="pages",
        table_name=lambda item: item.pop("target_table", "pages"),
        write_disposition="merge",
        primary_key="id",
        columns={
            "id": {"data_type": "text"},
            "database_id": {"data_type": "text"},
            "title": {"data_type": "text"},
            "content": {"data_type": "text"},
            "url": {"data_type": "text"},
            "created_time": {"data_type": "timestamp"},
            "last_edited_time": {"data_type": "timestamp"},
            "processed": {"data_type": "bigint"}
        }
    )
    def fetch_manual_notion_pages():
        # 1. Fetch pages from all discovered child databases
        for db in databases:
            db_id = db["id"]
            db_name = db["name"]
            prefix = db.get("prefix", "")
            target_table = derive_table_name(prefix, db_name)

            logger.info(f"Querying Notion database '{db_name}' ({db_id}) -> target table '{target_table}'")

            query_url = f"https://api.notion.com/v1/databases/{db_id}/query"
            query_body = {
                "filter": {
                    "timestamp": "last_edited_time",
                    "last_edited_time": {
                        "on_or_after": start_date
                    }
                },
                "page_size": 100
            }

            try:
                res = requests.post(query_url, headers=headers, json=query_body, timeout=15)
                if res.status_code != 200:
                    logger.error(f"Failed to query database {db_id}: Status {res.status_code}")
                    continue

                pages = res.json().get("results", [])
                for page in pages:
                    page_id = page.get("id")
                    if not page_id:
                        continue

                    title = ""
                    props = page.get("properties", {})
                    for key, prop in props.items():
                        if prop and prop.get("type") == "title":
                            title_parts = prop.get("title", [])
                            title = "".join([t.get("plain_text", "") for t in title_parts])
                            break
                    if not title:
                        title = page.get("url", "Untitled Page")

                    text_content = ""
                    try:
                        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                        blocks_res = requests.get(blocks_url, headers=headers, timeout=10)
                        if blocks_res.status_code == 200:
                            for b in blocks_res.json().get("results", []):
                                btype = b.get("type")
                                bcontent = b.get(btype, {})
                                if bcontent and "rich_text" in bcontent:
                                    text_content += "".join([t.get("plain_text", "") for t in bcontent["rich_text"]]) + "\n"
                    except Exception as block_err:
                        logger.warning(f"Error fetching page blocks for {page_id}: {block_err}")

                    yield {
                        "target_table": target_table,
                        "id": page_id,
                        "database_id": db_id,
                        "title": title,
                        "content": text_content.strip(),
                        "url": page.get("url", ""),
                        "created_time": page.get("created_time", now.isoformat()),
                        "last_edited_time": page.get("last_edited_time", now.isoformat()),
                        "processed": 0
                    }
            except Exception as db_err:
                logger.error(f"Error querying database {db_id}: {db_err}")

        # 2. Fetch pages for all discovered child subpages
        for sub in subpages:
            subpage_id = sub["id"]
            subpage_title = sub["title"]
            parent_id = sub["parent_id"]
            prefix = sub.get("prefix", "")
            target_table = derive_table_name(prefix, subpage_title)

            logger.info(f"Ingesting subpage '{subpage_title}' ({subpage_id}) -> target table '{target_table}'")
            text_content = ""
            try:
                blocks_url = f"https://api.notion.com/v1/blocks/{subpage_id}/children"
                blocks_res = requests.get(blocks_url, headers=headers, timeout=10)
                if blocks_res.status_code == 200:
                    for b in blocks_res.json().get("results", []):
                        btype = b.get("type")
                        bcontent = b.get(btype, {})
                        if bcontent and "rich_text" in bcontent:
                            text_content += "".join([t.get("plain_text", "") for t in bcontent["rich_text"]]) + "\n"
            except Exception as sub_err:
                logger.warning(f"Error fetching text blocks for subpage {subpage_id}: {sub_err}")

            yield {
                "target_table": target_table,
                "id": subpage_id,
                "database_id": parent_id,
                "title": subpage_title,
                "content": text_content.strip(),
                "url": f"https://notion.so/{subpage_id.replace('-', '')}",
                "created_time": now.isoformat(),
                "last_edited_time": now.isoformat(),
                "processed": 0
            }

    pipeline = create_postgres_pipeline(
        pipeline_name="ingest_notion_manual",
        dataset_name="s_notion"
    )

    info = pipeline.run(fetch_manual_notion_pages())
    logger.info(f"Notion Manual Data Ingestion completed successfully: {info}")
    return info


if __name__ == "__main__":
    run_ingestion()
