import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

cdp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'cdp'))
if cdp_dir not in sys.path:
    sys.path.insert(0, cdp_dir)

from processors.process_linkedin_connections import process_linkedin_connections, generate_company_domain
import utils as cdp_utils
import main as cdp_main
app = cdp_main.app

if cdp_dir in sys.path:
    sys.path.remove(cdp_dir)
if 'utils' in sys.modules:
    del sys.modules['utils']
if 'main' in sys.modules:
    del sys.modules['main']


def test_generate_company_domain():
    assert generate_company_domain("Acme Inc!") == "acme.com"
    assert generate_company_domain("Delivery Hero SE") == "deliveryhero.com"
    assert generate_company_domain("Fashion Digital GmbH & Co. KG") == "fashiondigital.com"
    assert generate_company_domain("") == ""
    assert generate_company_domain(None) == ""


def test_process_linkedin_connections_no_rows():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.mappings.return_value.all.return_value = []

    with patch('processors.process_linkedin_connections.get_db_engine', return_value=mock_engine):
        result = process_linkedin_connections()
        assert result["status"] == "success"
        assert result["processed_count"] == 0
        assert result["accounts_processed"] == 0


def test_process_linkedin_connections_blank_row_skipped():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    blank_row = {
        "id": "conn-blank",
        "first_name": "",
        "last_name": "",
        "profile_url": "",
        "email_address": "",
        "company": "",
        "position": ""
    }
    mock_conn.execute.return_value.mappings.return_value.all.return_value = [blank_row]

    with patch('processors.process_linkedin_connections.get_db_engine', return_value=mock_engine):
        result = process_linkedin_connections()
        assert result["status"] == "success"
        assert result["processed_count"] == 0
        assert result["accounts_processed"] == 0


def test_process_linkedin_connections_with_company_rows():
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
    mock_conn.execute.return_value.scalar.side_effect = ["person-uuid-1", "account-uuid-1"]

    with patch('processors.process_linkedin_connections.get_db_engine', return_value=mock_engine):
        result = process_linkedin_connections()
        assert result["status"] == "success"
        assert result["processed_count"] == 1
        assert result["accounts_processed"] == 1
        assert result["relationships_processed"] == 1


def test_cdp_utils():
    logger = cdp_utils.setup_logging("test-logger")
    assert logger.name == "test-logger"
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}):
        engine = cdp_utils.get_db_engine()
        assert engine is not None


def test_cdp_fastapi_endpoints():
    client = TestClient(app)
    
    # Health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "cdp"}

    # Process endpoint success
    with patch.object(cdp_main, 'process_linkedin_connections', return_value={"status": "success", "processed_count": 5}):
        response = client.post("/process/linkedin_connections")
        assert response.status_code == 200
        assert response.json()["processed_count"] == 5

    # Process endpoint error handling
    with patch.object(cdp_main, 'process_linkedin_connections', side_effect=Exception("Database connection error")):
        response = client.post("/process/linkedin_connections")
        assert response.status_code == 500
        assert response.json()["detail"] == "Database connection error"

    # Manual data endpoint success
    with patch.object(cdp_main, 'process_manual_data', return_value={"status": "success", "leads_processed": 3}):
        response = client.post("/process/manual_data")
        assert response.status_code == 200
        assert response.json()["leads_processed"] == 3


def test_process_manual_data_no_tables():
    from processors.process_manual_data import process_manual_data
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch('processors.process_manual_data.get_db_engine', return_value=mock_engine):
        result = process_manual_data()
        assert result["status"] == "success"
        assert result["leads_processed"] == 0
        assert result["persons_processed"] == 0


