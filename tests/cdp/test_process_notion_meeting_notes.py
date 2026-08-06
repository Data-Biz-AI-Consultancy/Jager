import os
import sys
import importlib.util
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

cdp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src', 'cdp'))
if cdp_dir not in sys.path:
    sys.path.insert(0, cdp_dir)

# Import cdp main module explicitly to avoid conflict with dapp main module
cdp_main_spec = importlib.util.spec_from_file_location("cdp_main_module", os.path.join(cdp_dir, "main.py"))
cdp_main = importlib.util.module_from_spec(cdp_main_spec)
sys.modules["cdp_main_module"] = cdp_main
cdp_main_spec.loader.exec_module(cdp_main)

from processors.process_notion_meeting_notes import process_notion_meeting_notes

app = cdp_main.app
client = TestClient(app)


def test_process_notion_meeting_notes_no_table():
    mock_jager_engine = MagicMock()
    mock_cdp_engine = MagicMock()
    mock_jager_conn = MagicMock()
    mock_cdp_conn = MagicMock()

    mock_jager_engine.begin.return_value.__enter__.return_value = mock_jager_conn
    mock_cdp_engine.begin.return_value.__enter__.return_value = mock_cdp_conn

    # Table check returns None (no table)
    mock_jager_conn.execute.return_value.fetchone.return_value = None

    def mock_get_engine(default_url=None, env_var="DATABASE_URL"):
        if env_var == "JAGER_DATABASE_URL":
            return mock_jager_engine
        return mock_cdp_engine

    with patch('processors.process_notion_meeting_notes.get_db_engine', side_effect=mock_get_engine):
        res = process_notion_meeting_notes()
        assert res["intake_processed"] == 0
        assert res["activities_processed"] == 0


def test_process_notion_meeting_notes_with_rows():
    mock_jager_engine = MagicMock()
    mock_cdp_engine = MagicMock()
    mock_jager_conn = MagicMock()
    mock_cdp_conn = MagicMock()

    mock_jager_engine.begin.return_value.__enter__.return_value = mock_jager_conn
    mock_cdp_engine.begin.return_value.__enter__.return_value = mock_cdp_conn

    # Table check returns valid row
    mock_jager_conn.execute.return_value.fetchone.return_value = (1,)

    # s_notion.meeting_notes query returns 1 row
    mock_note = {
        "page_id": "note-123",
        "database_name": "FaDi meeting notes",
        "title": "Strategy Sync",
        "created_time": "2026-08-01T10:00:00Z",
        "last_edited_time": "2026-08-01T10:00:00Z",
        "properties": {"Attendees": "Alice, Bob"},
        "icon": None,
        "cover_url": None,
        "url": "https://notion.so/note-123",
        "text_content": "Discussed roadmap.",
        "to_dos": ["Send proposal"],
        "fetched_at": "2026-08-01T10:00:00Z"
    }

    mock_jager_conn.execute.return_value.mappings.return_value.fetchall.return_value = [mock_note]

    # cdp.activities_notion_meeting_notes query returns 1 intake row
    mock_intake = {
        "page_id": "note-123",
        "person_id": None,
        "client_account_id": None,
        "database_name": "FaDi meeting notes",
        "title": "Strategy Sync",
        "meeting_date": "2026-08-01T10:00:00Z",
        "attendees": "Alice, Bob",
        "summary_or_content": "Discussed roadmap.",
        "to_dos": ["Send proposal"],
        "url": "https://notion.so/note-123"
    }

    mock_cdp_conn.execute.return_value.mappings.return_value.fetchall.return_value = [mock_intake]

    def mock_get_engine(default_url=None, env_var="DATABASE_URL"):
        if env_var == "JAGER_DATABASE_URL":
            return mock_jager_engine
        return mock_cdp_engine

    with patch('processors.process_notion_meeting_notes.get_db_engine', side_effect=mock_get_engine):
        res = process_notion_meeting_notes()
        assert res["status"] == "success"
        assert res["intake_processed"] == 1
        assert res["activities_processed"] == 1


def test_endpoint_notion_meeting_notes():
    with patch.object(cdp_main, 'process_notion_meeting_notes') as mock_proc:
        mock_proc.return_value = {"status": "success", "intake_processed": 1, "activities_processed": 1}
        response = client.post("/process/notion_meeting_notes")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
