import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))


def _make_mock_engine():
    """Build a mock SQLAlchemy engine/connection — no real DB required."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.scalar.return_value = "mock-uuid"
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_cm.__exit__ = MagicMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_cm
    return mock_engine


def test_cdp_seed_ingestion():
    mock_engine = _make_mock_engine()

    from oltp import ingest_seeds

    # Mock the DB engine
    with patch.object(ingest_seeds, 'get_db_engine', return_value=mock_engine):
        res = ingest_seeds.run_ingestion()

    assert res["status"] == "success"
    # 3 substack rows + 3 cdp rows = 6 records (from local data/seed or tests/fixtures/seed)
    assert res["records_processed"] >= 3
