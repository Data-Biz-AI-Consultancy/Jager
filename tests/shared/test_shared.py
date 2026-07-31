from shared.db import setup_logging, get_db_engine, create_motherduck_pipeline, create_postgres_pipeline, get_http_headers

def test_shared_logging():
    logger = setup_logging("test_logger")
    assert logger.name == "test_logger"

def test_shared_get_db_engine():
    engine = get_db_engine("postgresql://jager:jager@localhost:5432/jager")
    assert engine is not None


def test_shared_http_headers():
    headers = get_http_headers()
    assert "User-Agent" in headers
