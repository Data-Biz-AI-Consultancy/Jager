import os
import logging
from sqlalchemy import create_engine

def setup_logging(name: str):
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

def get_db_engine():
    db_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@localhost:5432/jager")
    return create_engine(db_url)
