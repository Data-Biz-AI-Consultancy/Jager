import datetime
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy import Engine, text

logger = logging.getLogger("ml-service.backtest")

def run_backtest(
    engine: Engine,
    symbol: str,
    lag_days: int = 5,
    exclude_last_days: int = 14,
    predict_days: int = 7
):
    # 1. Fetch historical data from DB
    query = text("""
        SELECT price_timestamp, close_price, open_price, volume
        FROM yahoo_finance_stock_prices
        WHERE symbol = :symbol
        ORDER BY price_timestamp ASC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"symbol": symbol})
        
    if df.empty:
        raise ValueError(f"No historical price data found for {symbol}.")
        
    # Preprocess
    df['price_timestamp'] = pd.to_datetime(df['price_timestamp'])
    df['date'] = df['price_timestamp'].dt.date
    df = df.drop_duplicates(subset=['date'], keep='last').sort_values('date').reset_index(drop=True)
    
    total_records = len(df)
    if total_records < exclude_last_days + lag_days + 2:
        raise ValueError(
            f"Not enough data to run backtest. Total records: {total_records}. "
            f"Required at least: exclude_last_days ({exclude_last_days}) + lag_days ({lag_days}) + 2."
        )
        
    # 2. Split into Train Base and Validation
    # We train on data up to the last `exclude_last_days`
    df_train_base = df.iloc[:-exclude_last_days].copy().reset_index(drop=True)
    
    # 3. Build Lag Features for training
    actual_lags = lag_days
    for i in range(1, actual_lags + 1):
        df_train_base[f'lag_{i}'] = df_train_base['close_price'].shift(i)
        
    df_train_clean = df_train_base.dropna().reset_index(drop=True)
    if len(df_train_clean) < 1:
        raise ValueError("Insufficient training data after building lag features.")
        
    feature_cols = [f'lag_{i}' for i in range(1, actual_lags + 1)]
    X_train = df_train_clean[feature_cols].values
    y_train = df_train_clean['close_price'].values
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    r2_score = float(model.score(X_train, y_train))
    
    # 4. Generate Autoregressive Predictions
    # Start lags from the last training row
    recent_lags = [float(df_train_base.iloc[-1]['close_price'])] + [
        float(df_train_base.iloc[-1][f'lag_{i}']) for i in range(1, actual_lags)
    ]
    
    last_actual_price = float(df_train_base.iloc[-1]['close_price'])
    
    # The actual values we are comparing against are the first `predict_days` of the excluded dataset
    df_excluded = df.iloc[-exclude_last_days:].copy().reset_index(drop=True)
    
    comparison_results = []
    absolute_errors = []
    squared_errors = []
    percentage_errors = []
    
    limit = min(predict_days, len(df_excluded))
    
    for idx in range(limit):
        features_arr = np.array(recent_lags[:actual_lags]).reshape(1, -1)
        predicted_price = float(model.predict(features_arr)[0])
        
        actual_row = df_excluded.iloc[idx]
        actual_date = actual_row['date']
        actual_price = float(actual_row['close_price'])
        
        # Calculate error metrics
        abs_err = abs(predicted_price - actual_price)
        sq_err = (predicted_price - actual_price) ** 2
        pct_err = abs_err / actual_price if actual_price != 0 else 0
        
        absolute_errors.append(abs_err)
        squared_errors.append(sq_err)
        percentage_errors.append(pct_err)
        
        comparison_results.append({
            "date": str(actual_date),
            "predicted_price": round(predicted_price, 2),
            "actual_price": round(actual_price, 2),
            "absolute_error": round(abs_err, 2),
            "percentage_error": round(pct_err * 100, 2)
        })
        
        # Autoregressive update: prepend predicted price, drop oldest
        recent_lags = [predicted_price] + recent_lags[:-1]
        
    # Compute summary metrics
    mae = float(np.mean(absolute_errors)) if absolute_errors else 0.0
    rmse = float(np.sqrt(np.mean(squared_errors))) if squared_errors else 0.0
    mape = float(np.mean(percentage_errors) * 100) if percentage_errors else 0.0
    
    return {
        "symbol": symbol,
        "train_records": len(df_train_clean),
        "r2_score": r2_score,
        "metrics": {
            "mean_absolute_error": round(mae, 2),
            "root_mean_squared_error": round(rmse, 2),
            "mean_absolute_percentage_error_percent": round(mape, 2)
        },
        "results": comparison_results
    }
