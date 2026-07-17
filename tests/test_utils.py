import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock

# Add src/data_pipelines to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))

# Mock DLT modules to prevent actual initialization issues during imports
sys.modules['dlt'] = MagicMock()
sys.modules['dlt.destinations'] = MagicMock()

from common import utils

def test_setup_logging():
    logger = utils.setup_logging("test-logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test-logger"

@patch('common.utils.create_engine')
def test_get_db_engine(mock_create_engine):
    utils.get_db_engine()
    mock_create_engine.assert_called_once()

def test_get_http_headers():
    headers = utils.get_http_headers()
    assert isinstance(headers, dict)
    assert "User-Agent" in headers
    assert "Jager" in headers["User-Agent"]

@patch('dlt.pipeline')
def test_create_motherduck_pipeline(mock_pipeline):
    os.environ["MOTHERDUCK_TOKEN"] = "dummy_token"
    utils.create_motherduck_pipeline("test_pipe", "test_dataset")
    mock_pipeline.assert_called_once()

@patch('dlt.pipeline')
def test_create_postgres_pipeline(mock_pipeline):
    utils.create_postgres_pipeline("test_pipe", "test_dataset")
    mock_pipeline.assert_called_once()
