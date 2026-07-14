import os
import sys
import logging
import dlt
from dlt.destinations import motherduck
from sqlalchemy import create_engine

def setup_logging(name: str):
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(name)

def get_db_engine():
    pg_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")
    return create_engine(pg_url)

def create_motherduck_pipeline(pipeline_name: str, dataset_name: str):
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    motherduck_database = os.getenv("MOTHERDUCK_DATABASE", "staging")

    if not motherduck_token:
        # Using a default root logger info/error since logger name might vary
        logging.error("MOTHERDUCK_TOKEN environment variable is not set")
        sys.exit(1)

    # Set DLT configurations
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
