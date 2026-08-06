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
    assert "Get Active Databases" in node_names
    assert "Fetch Monitored Pages" in node_names
    assert "Parse Notion Pages" in node_names
    assert "Route Entity Type" in node_names
    assert "Insert/Upsert Notion Pages" in node_names
    assert "Insert/Upsert Notion Meeting Notes" in node_names

    # Verify meeting notes databases in Get Active Databases node
    get_dbs_node = next(n for n in data.get("nodes", []) if n.get("name") == "Get Active Databases")
    js_code = get_dbs_node["parameters"]["jsCode"]
    assert "3876e98d4ef8807eab9be1b0b029246c" in js_code  # Interview Meeting notes
    assert "3876e98d4ef880a6a61ae99d8912694f" in js_code  # Meetups & Seminars
    assert "3a36e98d4ef88084a1aec60052a3cb80" in js_code  # FaDi meeting notes
