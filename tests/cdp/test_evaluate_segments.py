import os
import sys
import importlib
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

cdp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'src', 'cdp'))
if cdp_dir not in sys.path:
    sys.path.insert(0, cdp_dir)
else:
    sys.path.remove(cdp_dir)
    sys.path.insert(0, cdp_dir)

if 'main' in sys.modules:
    del sys.modules['main']

from processors.evaluate_segments import (
    evaluate_segments,
    ensure_seed_segments,
    evaluate_person_segments,
    evaluate_lead_segments,
    PERSON_SEGMENT_RULES,
    LEAD_SEGMENT_RULES,
)
import main as cdp_main

@pytest.fixture(autouse=True, scope="module")
def cleanup_sys_modules():
    yield
    if 'main' in sys.modules:
        del sys.modules['main']
    if 'utils' in sys.modules:
        del sys.modules['utils']
    if cdp_dir in sys.path:
        sys.path.remove(cdp_dir)


client = TestClient(cdp_main.app)




def test_ensure_seed_segments():
    mock_conn = MagicMock()
    ensure_seed_segments(mock_conn)

    # Should execute insert statements for person (5) and lead (5) seeds
    assert mock_conn.execute.call_count >= 10


def test_evaluate_person_segments():
    mock_conn = MagicMock()
    # Mock person_segments query
    mock_conn.execute.return_value.fetchall.side_effect = [
        # cdp.person_segments fetchall
        [
            ("p-uuid-1", "clients_and_prospects", "Clients & Prospects", "dynamic", {"rule": "clients_and_prospects"}),
            ("p-uuid-2", "hiring_decision_makers", "Hiring Decision-Makers", "dynamic", {"rule": "hiring_decision_makers"}),
        ],
        # rule 1 matching persons
        [("person-123",)],
        # rule 2 matching persons
        [("person-456",), ("person-789",)],
    ]
    mock_conn.execute.return_value.scalar.side_effect = [1, 2, 0]
    mock_conn.execute.return_value.fetchone.return_value = ("p-uuid-gen", "general_network", "General Network")

    results = evaluate_person_segments(mock_conn)
    assert results["clients_and_prospects"] == 1
    assert results["hiring_decision_makers"] == 2


def test_evaluate_lead_segments():
    mock_conn = MagicMock()
    # Mock lead_segments query
    mock_conn.execute.return_value.fetchall.side_effect = [
        # cdp.lead_segments fetchall
        [
            ("l-uuid-1", "new_leads_no_followup_7d", "New Leads No Followup 7d", "dynamic", {"rule": "new_leads_no_followup_7d"}),
            ("l-uuid-2", "contract_pending", "Contract Pending", "dynamic", {"rule": "contract_pending"}),
        ],
        # rule 1 matching leads
        [("lead-111",)],
        # rule 2 matching leads
        [],
    ]

    results = evaluate_lead_segments(mock_conn)
    assert results["new_leads_no_followup_7d"] == 1
    assert results["contract_pending"] == 0



def test_evaluate_segments_full():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    mock_conn.execute.return_value.fetchall.return_value = []

    with patch('processors.evaluate_segments.get_db_engine', return_value=mock_engine):
        result = evaluate_segments()
        assert result["status"] == "success"
        assert "person_segments" in result
        assert "lead_segments" in result


def test_evaluate_segments_api_endpoint():
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    mock_conn.execute.return_value.fetchall.return_value = []

    with patch('processors.evaluate_segments.get_db_engine', return_value=mock_engine):
        response = client.post("/process/evaluate_segments")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
