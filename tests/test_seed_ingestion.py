import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))


def test_cdp_seed_ingestion():
    # Build a mock engine/connection that accepts all SQL calls without a real DB
    mock_conn = MagicMock()
    # Simulate RETURNING id by returning a scalar for each INSERT
    mock_conn.execute.return_value.scalar.return_value = "mock-uuid"
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_cm.__exit__ = MagicMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_cm

    with patch('common.utils.get_db_engine', return_value=mock_engine), \
         patch('oltp.ingest_seeds.get_db_engine', return_value=mock_engine):
        from oltp.ingest_seeds import run_ingestion
        res = run_ingestion()

    assert res["status"] == "success"
    assert res["records_processed"] > 0
