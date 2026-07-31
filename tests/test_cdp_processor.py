import os
import sys
import pytest
from unittest.mock import MagicMock, patch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.cdp.processors.process_linkedin_connections import process_linkedin_connections


def test_process_linkedin_connections_no_rows():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.mappings.return_value.all.return_value = []

    with patch('src.cdp.processors.process_linkedin_connections.get_db_engine', return_value=mock_engine):
        result = process_linkedin_connections()
        assert result["status"] == "success"
        assert result["processed_count"] == 0


def test_process_linkedin_connections_with_rows():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    fake_row = {
        "id": "conn-123",
        "first_name": "John",
        "last_name": "Doe",
        "profile_url": "https://linkedin.com/in/johndoe",
        "email_address": "john@example.com",
        "company": "Acme Inc",
        "position": "CEO"
    }
    mock_conn.execute.return_value.mappings.return_value.all.return_value = [fake_row]

    with patch('src.cdp.processors.process_linkedin_connections.get_db_engine', return_value=mock_engine):
        result = process_linkedin_connections()
        assert result["status"] == "success"
        assert result["processed_count"] == 1
        assert mock_conn.execute.call_count >= 2
