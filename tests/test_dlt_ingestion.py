import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src/dlt to Python path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/dlt')))

# Mock DLT and its destination module to avoid actual MotherDuck initialization during imports
sys.modules['dlt'] = MagicMock()
sys.modules['dlt.destinations'] = MagicMock()

# Mock the database engine creation and DLT pipeline creation
@pytest.fixture
def mock_dlt_utils():
    with patch('olap.utils.get_db_engine') as mock_engine, \
         patch('olap.utils.create_motherduck_pipeline') as mock_pipeline:
        
        # Setup mock db connections
        mock_conn = MagicMock()
        mock_engine.return_value.connect.return_value.__enter__.return_value = mock_conn
        
        # Setup mock pipeline
        mock_pipeline_inst = MagicMock()
        mock_pipeline.return_value = mock_pipeline_inst
        
        yield {
            'engine': mock_engine,
            'connection': mock_conn,
            'pipeline': mock_pipeline,
            'pipeline_inst': mock_pipeline_inst
        }

def test_ingest_buffer(mock_dlt_utils):
    from olap import ingest_buffer
    
    # Mock engine execution return value to return some dummy rows
    mock_dlt_utils['connection'].execute.return_value = []
    
    ingest_buffer.run_ingestion()
    
    # Verify pipeline was created and run
    mock_dlt_utils['pipeline'].assert_called_once_with(
        pipeline_name="buffer_ingestion_v3",
        dataset_name="s_buffer"
    )
    mock_dlt_utils['pipeline_inst'].run.assert_called_once()

def test_ingest_linkedin(mock_dlt_utils):
    from olap import ingest_linkedin
    
    mock_dlt_utils['connection'].execute.return_value = []
    
    ingest_linkedin.run_ingestion()
    
    mock_dlt_utils['pipeline'].assert_called_once_with(
        pipeline_name="linkedin_ingestion",
        dataset_name="s_linkedin"
    )
    mock_dlt_utils['pipeline_inst'].run.assert_called_once()

def test_ingest_zernio(mock_dlt_utils):
    from olap import ingest_zernio
    
    mock_dlt_utils['connection'].execute.return_value = []
    
    ingest_zernio.run_ingestion()
    
    mock_dlt_utils['pipeline'].assert_called_once_with(
        pipeline_name="zernio_ingestion",
        dataset_name="s_zernio"
    )
    mock_dlt_utils['pipeline_inst'].run.assert_called_once()
