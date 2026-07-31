import os
import sys
import re
import requests
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
import dlt

load_dotenv()

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, create_postgres_pipeline

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


def derive_table_name(prefix: str, entity_name: str, tool_name: str = "notion") -> str:
    cleaned_tool = to_snake_case(tool_name) or "notion"
    cleaned_prefix = to_snake_case(prefix)
    cleaned_entity = to_snake_case(entity_name)

    if cleaned_prefix:
        if cleaned_entity:
            if cleaned_entity.startswith(cleaned_prefix + "_"):
                target = cleaned_entity
            else:
                target = f"{cleaned_prefix}_{cleaned_entity}"
        else:
            target = f"{cleaned_prefix}_pages"
    else:
        target = cleaned_entity or "pages"

    return f"{cleaned_tool}__{target}"


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
        # Paginate through all blocks (Notion returns max 100 per request)
        has_more = True
        params = {"page_size": 100}
        while has_more:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code != 200:
                logger.warning(f"Could not fetch children for block {formatted_id}: Status {res.status_code}")
                break

            data = res.json()
            blocks = data.get("results", [])
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")
            if has_more and next_cursor:
                params["start_cursor"] = next_cursor
            else:
                has_more = False

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

                    # Recursively discover child sources under this subpage (any depth)
                    child_dbs, child_pages = discover_child_sources(
                        page_id,
                        current_prefix=child_prefix,
                        is_root=False,
                        visited=visited
                    )
                    databases.extend(child_dbs)
                    subpages.extend(child_pages)

    except Exception as e:
        logger.error(f"Error fetching child blocks for page {formatted_id}: {e}")

    return databases, subpages



def create_database_resource(db: dict, headers: dict, now_iso: str):
    db_id = db.get("id") or db.get("database_id")
    db_name = db["name"]
    prefix = db.get("prefix", "")
    table_name = derive_table_name(prefix, db_name, tool_name="notion")

    @dlt.resource(name=table_name, write_disposition="merge", primary_key="notion_id")
    def fetch_database_pages():
        logger.info(f"Ingesting Notion database '{db_name}' ({db_id}) -> table '{table_name}'")
        query_url = f"https://api.notion.com/v1/databases/{db_id}/query"
        has_more = True
        query_body = {"page_size": 100}

        while has_more:
            try:
                res = requests.post(query_url, headers=headers, json=query_body, timeout=15)
                if res.status_code != 200:
                    logger.error(f"Failed to query database {db_id}: Status {res.status_code}")
                    return

                data = res.json()
                pages = data.get("results", [])
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor")
                if has_more and next_cursor:
                    query_body["start_cursor"] = next_cursor
                else:
                    has_more = False

                for page in pages:
                    page_id = page.get("id")
                    if not page_id:
                        continue

                    props = page.get("properties", {})

                    # Extract each property as its own column using snake_case key
                    row = {
                        "notion_id": page_id,
                        "notion_database_id": db_id,
                        "notion_url": page.get("url", ""),
                        "notion_created_time": page.get("created_time", now_iso),
                        "notion_last_edited_time": page.get("last_edited_time", now_iso),
                    }

                    for prop_name, prop in props.items():
                        col_name = to_snake_case(prop_name)
                        if not col_name:
                            continue
                        vtype = prop.get("type")
                        val = None
                        if vtype == "title":
                            val = "".join([t.get("plain_text", "") for t in prop.get("title", [])])
                        elif vtype == "email":
                            val = prop.get("email")
                        elif vtype == "number":
                            val = prop.get("number")
                        elif vtype == "select":
                            val = prop.get("select", {}).get("name") if prop.get("select") else None
                        elif vtype == "multi_select":
                            val = ", ".join([ms.get("name", "") for ms in prop.get("multi_select", [])])
                        elif vtype == "rich_text":
                            val = "".join([t.get("plain_text", "") for t in prop.get("rich_text", [])])
                        elif vtype == "date":
                            val = prop.get("date", {}).get("start") if prop.get("date") else None
                        elif vtype == "checkbox":
                            val = prop.get("checkbox")
                        elif vtype == "url":
                            val = prop.get("url")
                        elif vtype == "phone_number":
                            val = prop.get("phone_number")
                        row[col_name] = val

                    yield row

            except Exception as db_err:
                logger.error(f"Error querying database {db_id}: {db_err}")
                return

    return fetch_database_pages



def create_subpages_resource(prefix: str, subpages: list, headers: dict, now_iso: str):
    table_name = derive_table_name(prefix, "subpages", tool_name="notion")

    @dlt.resource(name=table_name, write_disposition="merge", primary_key="id")
    def fetch_subpages():
        for sub in subpages:
            subpage_id = sub["id"]
            subpage_title = sub["title"]
            parent_id = sub["parent_id"]

            logger.info(f"Ingesting subpage '{subpage_title}' ({subpage_id}) -> table '{table_name}'")
            text_content = ""
            try:
                blocks_url = f"https://api.notion.com/v1/blocks/{subpage_id}/children"
                blocks_res = requests.get(blocks_url, headers=headers, timeout=5)
                if blocks_res.status_code == 200:
                    for b in blocks_res.json().get("results", []):
                        btype = b.get("type")
                        bcontent = b.get(btype, {})
                        if bcontent and "rich_text" in bcontent:
                            text_content += "".join([t.get("plain_text", "") for t in bcontent["rich_text"]]) + "\n"
            except Exception as sub_err:
                logger.warning(f"Error fetching text blocks for subpage {subpage_id}: {sub_err}")

            yield {
                "id": subpage_id,
                "database_id": parent_id,
                "title": subpage_title,
                "content": text_content.strip(),
                "url": f"https://notion.so/{subpage_id.replace('-', '')}",
                "created_time": now_iso,
                "last_edited_time": now_iso,
                "processed": 0
            }

    return fetch_subpages


def run_ingestion():
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    parent_page_id = os.getenv("NOTION_MANUAL_INGESTION_PAGE_ID", "3ad6e98d4ef8808e90e5d12894842709")
    logger.info(f"Starting Notion Manual Data Ingestion for parent page {parent_page_id}")

    headers = get_notion_headers()
    databases, subpages = discover_child_sources(parent_page_id, is_root=True)

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

    now_iso = datetime.now(timezone.utc).isoformat()
    resources = []

    for db in databases:
        res_fn = create_database_resource(db, headers, now_iso)
        resources.append(res_fn())

    if subpages:
        grouped_subpages = defaultdict(list)
        for sub in subpages:
            grouped_subpages[sub.get("prefix", "")].append(sub)
        for prefix, p_subpages in grouped_subpages.items():
            res_fn = create_subpages_resource(prefix, p_subpages, headers, now_iso)
            resources.append(res_fn())

    if not resources:
        logger.warning("No resources to ingest.")
        return None

    pipeline = create_postgres_pipeline(
        pipeline_name="ingest_notion_manual",
        dataset_name="s_manual"
    )

    info = pipeline.run(resources)
    logger.info(f"Notion Manual Data Ingestion completed successfully: {info}")
    return info


if __name__ == "__main__":
    run_ingestion()
