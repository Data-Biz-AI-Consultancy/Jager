import json
import os


def test_dapp_connectors_notion_substack_workflow_structure():
    """Notion/Substack VectorDB refresh is scheduled via DAPP connectors, not data_ingestion."""
    workflow_path = os.path.join(
        os.path.dirname(__file__),
        "../../src/n8n/workflows/ai_memory/dapp_connectors_notion_substack.json",
    )
    assert os.path.exists(workflow_path), f"Workflow file does not exist: {workflow_path}"

    with open(workflow_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("id") == "dapp-connectors-notion-substack"
    assert data.get("name") == "DAPP Connectors - Notion & Substack"

    node_names = [n.get("name") for n in data.get("nodes", [])]
    assert "Schedule Trigger" in node_names
    assert "Trigger Notion Connector" in node_names
    assert "Trigger Substack Connector" in node_names
    assert len(data.get("nodes", [])) == 3

    notion = next(n for n in data["nodes"] if n["name"] == "Trigger Notion Connector")
    assert notion["type"] == "n8n-nodes-base.httpRequest"
    assert "/run/connectors/notion?mode=vectordb" in notion["parameters"]["url"]
    assert notion["parameters"].get("sendHeaders") is True
    headers = notion["parameters"]["headerParameters"]["parameters"]
    assert any(h.get("name") == "X-API-Key" for h in headers)

    substack = next(n for n in data["nodes"] if n["name"] == "Trigger Substack Connector")
    assert "/run/connectors/substack" in substack["parameters"]["url"]
    assert "dapp-api:8000" in substack["parameters"]["url"]


def test_notion_monitored_databases_seeds():
    oltp_seeds_path = os.path.join(os.path.dirname(__file__), "../../src/db/sql/oltp_seeds.sql")
    migrate_js_path = os.path.join(os.path.dirname(__file__), "../../src/db/migrate-db.js")

    with open(oltp_seeds_path, "r", encoding="utf-8") as f:
        oltp_seeds = f.read()

    with open(migrate_js_path, "r", encoding="utf-8") as f:
        migrate_js = f.read()

    target_dbs = [
        "3876e98d4ef8807eab9be1b0b029246c",  # Interview Meeting notes
        "3876e98d4ef880a6a61ae99d8912694f",  # Meetups & Seminars
        "3a36e98d4ef88084a1aec60052a3cb80",  # FaDi meeting notes
    ]

    for db_id in target_dbs:
        assert db_id in oltp_seeds, f"Database ID {db_id} missing from oltp_seeds.sql"
        assert "oltp_seeds.sql" in migrate_js, "migrate-db.js does not load oltp_seeds.sql"
