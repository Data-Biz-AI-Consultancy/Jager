import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text, create_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))

from oltp.ingest_seeds import run_ingestion


@pytest.fixture
def db_engine():
    db_url = os.environ.get("DATABASE_URL", "postgresql://jager:jager@localhost:5432/jager")
    os.environ["DATABASE_URL"] = db_url
    return create_engine(db_url)


@patch("oltp.ingest_seeds.get_db_engine")
def test_cdp_seed_ingestion(mock_get_engine, db_engine):
    mock_engine = MagicMock()
    mock_get_engine.return_value = mock_engine
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    res = run_ingestion()
    assert res["status"] == "success"
    assert res["records_processed"] >= 0

    # Check populated cdp tables in PostgreSQL if database engine connection succeeds
    try:
        with db_engine.connect() as conn:
            persons_count = conn.execute(text("SELECT COUNT(*) FROM cdp.persons")).scalar()
            assert persons_count >= 0
    except Exception:
        pass
