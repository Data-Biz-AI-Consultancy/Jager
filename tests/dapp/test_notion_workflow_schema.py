import os
import json

def test_notion_workflow_json_structure():
    workflow_path = os.path.join(os.path.dirname(__file__), '../../src/n8n/workflows/data_ingestion/data_ingestion_notion.json')
    assert os.path.exists(workflow_path), f"Workflow file does not exist: {workflow_path}"

    with open(workflow_path, 'r') as f:
        data = json.load(f)

    assert data.get("id") == "notion-ingestion-workflow"
    assert data.get("name") == "Data Ingestion - Notion"
    
    node_names = [n.get("name") for n in data.get("nodes", [])]
    assert "Schedule Trigger" in node_names
    assert "Ingest DB - Leadership & Management" in node_names
    assert "Ingest DB - FaDi meeting notes" in node_names
    assert len(data.get("nodes", [])) == 13

    db_node = next(n for n in data.get("nodes", []) if n.get("name") == "Ingest DB - Leadership & Management")
    assert db_node["type"] == "n8n-nodes-base.httpRequest"
    assert "/run/oltp/ingest_notion" in db_node["parameters"]["url"]


def test_notion_monitored_databases_seeds():
    oltp_seeds_path = os.path.join(os.path.dirname(__file__), '../../src/db/sql/oltp_seeds.sql')
    migrate_js_path = os.path.join(os.path.dirname(__file__), '../../src/db/migrate-db.js')

    with open(oltp_seeds_path, 'r') as f:
        oltp_seeds = f.read()

    with open(migrate_js_path, 'r') as f:
        migrate_js = f.read()

    target_dbs = [
        "3876e98d4ef8807eab9be1b0b029246c",  # Interview Meeting notes
        "3876e98d4ef880a6a61ae99d8912694f",  # Meetups & Seminars
        "3a36e98d4ef88084a1aec60052a3cb80"   # FaDi meeting notes
    ]

    for db_id in target_dbs:
        assert db_id in oltp_seeds, f"Database ID {db_id} missing from oltp_seeds.sql"
        assert "oltp_seeds.sql" in migrate_js, f"migrate-db.js does not load oltp_seeds.sql"

