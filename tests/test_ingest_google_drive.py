import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add src/data_pipelines to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))

from oltp.ingest_google_drive import get_mock_google_drive_subscribers, run_ingestion


def test_get_mock_google_drive_subscribers():
    subscribers = get_mock_google_drive_subscribers()
    assert len(subscribers) > 0
    assert "email" in subscribers[0]
    assert "company" in subscribers[0]


def test_fetch_google_drive_subscribers():
    subscribers = get_mock_google_drive_subscribers()
    assert len(subscribers) == 2
    assert subscribers[0]["id"] == "sub_gdrive_001"


@patch("oltp.ingest_google_drive.create_postgres_pipeline")
def test_run_ingestion(mock_create_pipeline):
    mock_pipeline = MagicMock()
    mock_create_pipeline.return_value = mock_pipeline
    mock_pipeline.run.return_value = "Load metadata"

    result = run_ingestion()

    mock_create_pipeline.assert_called_once_with(
        pipeline_name="google_drive_to_postgres",
        dataset_name="s_google_drive",
    )
    mock_pipeline.run.assert_called_once()
    assert result == "Load metadata"

