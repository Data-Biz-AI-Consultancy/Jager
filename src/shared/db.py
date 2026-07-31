import os
import logging
import sys
from sqlalchemy import create_engine


def setup_logging(name: str) -> logging.Logger:
    """Sets up standardized logging across services."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def get_db_engine(default_url: str = "postgresql://jager:jager@db:5432/jager"):
    """Returns a SQLAlchemy engine for PostgreSQL database connection."""
    pg_url = os.getenv("DATABASE_URL", default_url)
    return create_engine(pg_url)

def create_motherduck_pipeline(pipeline_name: str, dataset_name: str):
    """Creates a dlt pipeline configured for MotherDuck destination."""
    import dlt
    from dlt.destinations import motherduck
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    motherduck_database = os.getenv("MOTHERDUCK_DATABASE", "staging")

    if not motherduck_token:
        logging.error("MOTHERDUCK_TOKEN environment variable is not set")
        sys.exit(1)

    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"

    return dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=motherduck(
            credentials={
                "database": motherduck_database,
                "password": motherduck_token
            },
            loader_file_format="jsonl"
        ),
        dataset_name=dataset_name,
    )

def create_postgres_pipeline(pipeline_name: str, dataset_name: str):
    """Creates a dlt pipeline configured for PostgreSQL destination."""
    import dlt
    from dlt.destinations import postgres
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    db_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")
    return dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=postgres(credentials=db_url),
        dataset_name=dataset_name
    )

def get_http_headers() -> dict:
    """Returns standard HTTP headers for scraping/ingestion requests."""
    return {
        'User-Agent': 'Jager/1.0 (by /u/jager_developer)'
    }
