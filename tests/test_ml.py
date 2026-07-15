import os
import sys
import unittest.mock as mock
import pytest
import datetime
import pandas as pd
import numpy as np
import warnings


# Suppress deprecation warnings from third-party libraries
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add src/ml to Python path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/ml')))

# Create mock data
MOCK_DATES = ['2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05']
MOCK_PRICES = [100.0, 102.0, 101.0, 104.0, 105.0]

def get_mock_df():
    data = {
        'price_timestamp': [pd.Timestamp(d) for d in MOCK_DATES],
        'close_price': MOCK_PRICES,
        'open_price': [99.0, 101.0, 102.0, 103.0, 104.0],
        'volume': [1000, 1100, 1200, 1300, 1400]
    }
    df = pd.DataFrame(data)
    df['date'] = df['price_timestamp'].dt.date
    return df

# Global mock for sqlalchemy.create_engine to avoid connecting to postgres during imports/tests
mock_engine = mock.MagicMock()
sys.modules['sqlalchemy'] = mock.MagicMock()
import sqlalchemy
sqlalchemy.create_engine.return_value = mock_engine

# Global mock for duckdb to avoid dependency errors in environments where duckdb is not installed
sys.modules['duckdb'] = mock.MagicMock()
import duckdb


# Mock pandas read_sql
@pytest.fixture(autouse=True)
def mock_pandas_read_sql():
    with mock.patch('pandas.read_sql') as mock_read:
        mock_read.return_value = get_mock_df()
        yield mock_read

# Now import the modules safely
import train
import predict
import backtest
from fastapi.testclient import TestClient
import main

def test_train_model():
    mock_conn = mock.MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    
    # Run training with lag_days = 2
    model, df, r2_score, actual_lags = train.train_model(mock_engine, "^GSPC", lag_days=2)
    
    assert actual_lags == 2
    assert r2_score is not None
    assert 'lag_1' in df.columns
    assert 'lag_2' in df.columns
    assert len(df) == 3  # 5 rows minus 2 lags = 3 rows
    
    # Verify insert query was executed
    mock_conn.execute.assert_called()

def test_generate_predictions():
    mock_conn = mock.MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    
    # Train a model first
    model, df, r2_score, actual_lags = train.train_model(mock_engine, "^GSPC", lag_days=1)
    
    # Generate 3 days prediction
    predictions = predict.generate_predictions(
        engine=mock_engine,
        model=model,
        df=df,
        r2_score=r2_score,
        actual_lags=actual_lags,
        symbol="^GSPC",
        prediction_days=3
    )
    
    assert len(predictions) == 3
    assert predictions[0]['prediction_date'] == "2026-06-08" # next weekday after June 5

def test_run_backtest():
    # Test normal backtest with parameters requiring scaling
    res = backtest.run_backtest(
        engine=mock_engine,
        symbol="^GSPC",
        lag_days=5,
        exclude_last_days=14,
        predict_days=7
    )
    
    assert res['symbol'] == "^GSPC"
    assert res['parameter_adjustment']['adjusted'] is True
    # The actual applied values should have scaled to fit the 5 mock rows
    assert res['parameter_adjustment']['applied']['lag_days'] == 2
    assert res['parameter_adjustment']['applied']['exclude_last_days'] == 1
    assert len(res['results']) == 1

def test_api_predict():
    client = TestClient(main.app)
    
    # Mock train_model and generate_predictions
    with mock.patch('main.train_model') as mock_train, \
         mock.patch('main.generate_predictions') as mock_predict:
         
        mock_train.return_value = (mock.MagicMock(), get_mock_df(), 0.95, 2)
        mock_predict.return_value = [
            {"step": 1, "prediction_date": "2026-06-08", "predicted_close_price": 106.0, "trend": "UP", "reasoning": "Test"}
        ]
        
        response = client.post("/predict", json={"symbol": "^GSPC", "lag_days": 2, "prediction_days": 1})
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == "success"
        assert len(data['predictions']) == 1

def test_api_backtest():
    client = TestClient(main.app)
    
    with mock.patch('main.run_backtest') as mock_backtest:
        mock_backtest.return_value = {
            "symbol": "^GSPC",
            "train_records": 2,
            "r2_score": 1.0,
            "parameter_adjustment": {
                "adjusted": False,
                "requested": {"lag_days": 1, "exclude_last_days": 2, "predict_days": 2},
                "applied": {"lag_days": 1, "exclude_last_days": 2, "predict_days": 2}
            },
            "metrics": {"mean_absolute_error": 5.0, "root_mean_squared_error": 5.0, "mean_absolute_percentage_error_percent": 5.0},
            "results": []
        }
        
        response = client.post("/backtest", json={"symbol": "^GSPC", "lag_days": 1, "exclude_last_days": 2, "predict_days": 2})
        assert response.status_code == 200
        data = response.json()
        assert data['symbol'] == "^GSPC"
        assert 'metrics' in data

def test_get_next_trading_day():
    # Friday to Monday
    friday = datetime.date(2026, 6, 5) # Friday
    monday = predict.get_next_trading_day(friday)
    assert monday == datetime.date(2026, 6, 8)
    
    # Thursday to Friday
    thursday = datetime.date(2026, 6, 4)
    friday_next = predict.get_next_trading_day(thursday)
    assert friday_next == datetime.date(2026, 6, 5)

def test_api_evaluate():
    client = TestClient(main.app)
    
    mock_conn = mock.MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    
    # Mocking first query (find all predictions missing actual close price)
    # Mocking second query (find actual close price for date)
    mock_conn.execute.return_value.fetchall.return_value = [
        (1, "^GSPC", datetime.date(2026, 6, 4))
    ]
    mock_conn.execute.return_value.fetchone.return_value = (7584.31,)
    
    response = client.post("/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == "success"
    assert data['evaluated_records_count'] == 1

def test_linkedin_timeslot_train_validate():
    # Mock duckdb connection and execution
    mock_duckdb_conn = mock.MagicMock()
    
    # Mock fetch_historical_data query results
    # Simulating data for personal and company posts
    mock_df_personal = pd.DataFrame({
        'published_at_berlin': [pd.Timestamp('2026-06-01 10:00:00') + pd.Timedelta(days=i) for i in range(10)],
        'impressions': [1000]*10,
        'total_interactions': [50]*10,
        'engagement_rate': [0.05]*10
    })
    
    mock_df_company = pd.DataFrame({
        'published_at_berlin': [pd.Timestamp('2026-06-01 12:00:00') + pd.Timedelta(days=i) for i in range(10)],
        'impressions': [500]*10,
        'total_interactions': [25]*10,
        'engagement_rate': [0.05]*10
    })
    
    # Setup mock executes
    mock_duckdb_conn.execute.return_value.df.side_effect = [mock_df_personal, mock_df_company]
    # For SHOW TABLES IN ds_training query
    mock_duckdb_conn.execute.return_value.fetchall.return_value = [('model_registry',)]
    
    with mock.patch('linkedin_publishing_timeslot.train_pipeline.get_motherduck_connection', return_value=mock_duckdb_conn):
        from linkedin_publishing_timeslot.train_pipeline import train_and_validate
        res = train_and_validate()
        
        assert res['status'] == "success"
        assert 'personal' in res['results']
        assert 'company' in res['results']
        assert res['results']['personal']['status'] == 'trained'
        
        # Verify executed commands
        mock_duckdb_conn.execute.assert_any_call("CREATE SCHEMA IF NOT EXISTS ds_training;")
        mock_duckdb_conn.execute.assert_any_call("CREATE SCHEMA IF NOT EXISTS ds_prediction;")

def test_linkedin_timeslot_generate_predictions():
    mock_duckdb_conn = mock.MagicMock()
    mock_duckdb_conn.execute.return_value.fetchall.return_value = [('model_registry',)]
    
    # We mock pickle.loads to return a dummy trained model
    dummy_model = mock.MagicMock()
    dummy_model.predict.return_value = np.zeros(168)
    
    with mock.patch('linkedin_publishing_timeslot.predict_pipeline.get_motherduck_connection', return_value=mock_duckdb_conn), \
         mock.patch('pickle.loads', return_value=dummy_model):
        from linkedin_publishing_timeslot.predict_pipeline import generate_predictions as generate_linkedin_predictions
        res = generate_linkedin_predictions()



        
        assert res['status'] == "success"
        assert 'personal' in res['results']
        assert 'company' in res['results']

def test_api_linkedin_timeslot_train_validate():
    client = TestClient(main.app)
    
    with mock.patch('main.train_and_validate') as mock_train:
        mock_train.return_value = {
            "status": "success",
            "results": {
                "personal": {"status": "trained", "sample_size": 10, "r2_score": 1.0, "val_mae": 0.0},
                "company": {"status": "trained", "sample_size": 10, "r2_score": 1.0, "val_mae": 0.0}
            }
        }
        
        response = client.post("/linkedin-timeslot/train-validate")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == "success"
        assert 'personal' in data['results']

def test_api_linkedin_timeslot_predict():
    client = TestClient(main.app)
    
    with mock.patch('main.generate_linkedin_predictions') as mock_predict:
        mock_predict.return_value = {
            "status": "success",
            "results": {
                "personal": {"prediction_type": "ml_model", "top_slots": []},
                "company": {"prediction_type": "ml_model", "top_slots": []}
            }
        }
        
        response = client.post("/linkedin-timeslot/predict")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == "success"
        assert data['results']['personal']['prediction_type'] == 'ml_model'


