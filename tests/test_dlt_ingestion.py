import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Add src/data_pipelines to Python path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/data_pipelines')))


# Mock DLT and its destination module to avoid actual MotherDuck initialization during imports
sys.modules['dlt'] = MagicMock()
sys.modules['dlt.destinations'] = MagicMock()

# Mock the database engine creation and DLT pipeline creation
@pytest.fixture
def mock_dlt_utils():
    with patch('common.utils.get_db_engine') as mock_engine, \
         patch('common.utils.create_motherduck_pipeline') as mock_pipeline:
        
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

def test_ingest_substack(mock_dlt_utils):
    from olap import ingest_substack
    
    mock_dlt_utils['connection'].execute.return_value = []
    
    ingest_substack.run_ingestion()
    
    mock_dlt_utils['pipeline'].assert_called_once_with(
        pipeline_name="substack_ingestion",
        dataset_name="s_substack"
    )
    mock_dlt_utils['pipeline_inst'].run.assert_called_once()


@patch('requests.get')
@patch('feedparser.parse')
def test_ingest_wordpress(mock_feedparser, mock_get, mock_dlt_utils):
    from oltp import ingest_wordpress
    
    # Mock active feeds query response
    mock_dlt_utils['connection'].execute.return_value = [
        {"id": 1, "name": "Towards Data Science", "feed_url": "https://towardsdatascience.com/feed/"}
    ]
    
    # Mock requests.get returning a dummy status
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<xml></xml>"
    mock_get.return_value = mock_resp
    
    # Mock feedparser.parse returning some entries
    mock_feed = MagicMock()
    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda key, default=None: {
        "id": "https://towardsdatascience.com/?p=609803",
        "link": "https://towardsdatascience.com/?p=609803",
        "title": "Test Title",
        "summary": "<p>Test Content</p>",
        "author": "Omer Rosenbaum",
        "published_parsed": (2026, 7, 17, 10, 0, 0, 4, 198, 0)
    }.get(key, default)
    mock_feed.entries = [mock_entry]
    mock_feedparser.return_value = mock_feed
    
    # Patch dlt.pipeline to mock pipeline creation and return mock pipeline instance
    with patch('dlt.pipeline') as mock_dlt_pipeline:
        mock_pipeline_inst = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline_inst
        
        ingest_wordpress.run_ingestion()
        
        mock_dlt_pipeline.assert_called_once()
        mock_pipeline_inst.run.assert_called_once()


@patch('requests.get')
def test_ingest_yahoo_finance(mock_get, mock_dlt_utils):
    from oltp import ingest_yahoo_finance
    
    # Mock requests.get returning a mock response with Yahoo Finance JSON
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "^GSPC"},
                    "timestamp": [1784279536],
                    "indicators": {
                        "quote": [
                            {
                                "open": [5000.0],
                                "high": [5010.0],
                                "low": [4990.0],
                                "close": [5005.0],
                                "volume": [1000000.0]
                            }
                        ]
                    }
                }
            ]
        }
    }
    mock_get.return_value = mock_resp
    
    # Patch dlt.pipeline
    with patch('dlt.pipeline') as mock_dlt_pipeline:
        mock_pipeline_inst = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline_inst
        
        ingest_yahoo_finance.run_ingestion()
        
        mock_dlt_pipeline.assert_called_once()
        mock_pipeline_inst.run.assert_called_once()


@patch('requests.get')
def test_ingest_eurostat_fx(mock_get, mock_dlt_utils):
    from oltp import ingest_eurostat_fx
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "size": [1, 1, 1, 2, 2],
        "value": {
            "0": 1.08,  # USD currency=0, time=0
            "1": 1.09,  # USD currency=0, time=1
            "2": 8.42,  # HKD currency=1, time=0
            "3": 8.45   # HKD currency=1, time=1
        },
        "dimension": {
            "currency": {
                "category": {
                    "index": {"USD": 0, "HKD": 1}
                }
            },
            "time": {
                "category": {
                    "index": {"2026-07-16": 0, "2026-07-17": 1}
                }
            }
        }
    }
    mock_get.return_value = mock_resp
    
    with patch('dlt.pipeline') as mock_dlt_pipeline:
        mock_pipeline_inst = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline_inst
        
        ingest_eurostat_fx.run_ingestion()
        
        mock_dlt_pipeline.assert_called_once()
        mock_pipeline_inst.run.assert_called_once()


def test_reverse_etl_missing_token():
    from olap import reverse_etl
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            reverse_etl.run_reverse_etl()
        assert exc_info.value.code == 1


@patch('duckdb.connect')
def test_reverse_etl_success(mock_duckdb_connect):
    from olap import reverse_etl
    
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.description = [('id',), ('name',)]
    mock_res.fetchall.return_value = [(1, 'test_item')]
    mock_conn.execute.return_value = mock_res
    mock_duckdb_connect.return_value = mock_conn
    
    # Mock dlt.resource decorator to pass through the function and set metadata
    def mock_resource_decorator(name=None, write_disposition=None):
        def decorator(func):
            func.name = name
            func.write_disposition = write_disposition
            return func
        return decorator

    with patch.dict(os.environ, {"MOTHERDUCK_TOKEN": "test_token", "MOTHERDUCK_DATABASE": "staging"}), \
         patch('dlt.resource', side_effect=mock_resource_decorator), \
         patch('dlt.pipeline') as mock_dlt_pipeline:
        
        mock_pipeline_inst = MagicMock()
        mock_dlt_pipeline.return_value = mock_pipeline_inst
        
        reverse_etl.run_reverse_etl()
        
        # Verify duckdb connected with expected parameters
        mock_duckdb_connect.assert_called_once_with("md:staging?token=test_token")
        
        # Verify pipeline initialized with s_motherduck destination dataset
        mock_dlt_pipeline.assert_called_once()
        _, kwargs = mock_dlt_pipeline.call_args
        assert kwargs.get('pipeline_name') == "reverse_etl_motherduck"
        assert kwargs.get('dataset_name') == "s_motherduck"
        
        # Verify pipeline.run was called with 5 resources
        mock_pipeline_inst.run.assert_called_once()
        resources_arg = mock_pipeline_inst.run.call_args[0][0]
        assert len(resources_arg) == 5
        
        # Test resource generators yield correct dictionary data
        for resource_func in resources_arg:
            generator = resource_func()
            yielded_item = next(generator)
            assert yielded_item == {'id': 1, 'name': 'test_item'}
            
        # Verify connection close was executed in finally block
        mock_conn.close.assert_called_once()





