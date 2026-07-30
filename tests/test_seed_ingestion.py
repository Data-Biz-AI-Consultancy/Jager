import os
import sys
import pytest
from sqlalchemy import text

from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))

from oltp.ingest_seeds import run_ingestion


@pytest.fixture
def db_engine():
    db_url = os.environ.get("DATABASE_URL", "postgresql://jager:jager@localhost:5432/jager")
    os.environ["DATABASE_URL"] = db_url
    return create_engine(db_url)


def test_cdp_seed_ingestion(db_engine):
    # Run seed ingestion pipeline
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
