import logging
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy import Engine, text

logger = logging.getLogger("ml-service.train")

def train_model(engine: Engine, symbol: str, lag_days: int):
    # 1. Fetch historical data from DB
    query = text("""
        SELECT price_timestamp, close_price, open_price, volume
        FROM yahoo_finance_stock_prices
        WHERE symbol = :symbol
        ORDER BY price_timestamp ASC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"symbol": symbol})
        
    if df.empty or len(df) < 2:
        raise ValueError(f"Not enough historical price data for {symbol}. Required: at least 2 records.")
    
    # Preprocess
    df['price_timestamp'] = pd.to_datetime(df['price_timestamp'])
    df['date'] = df['price_timestamp'].dt.date
    # Drop duplicates by date, keeping the last one
    df = df.drop_duplicates(subset=['date'], keep='last').sort_values('date').reset_index(drop=True)
    
    # Dynamic adjustment of lag_days based on available unique dates
    actual_lags = lag_days
    if len(df) <= actual_lags:
        actual_lags = max(1, len(df) - 2)
        logger.warning(f"Insufficient data for requested lag_days={lag_days}. Dynamically reducing to {actual_lags}")
        
    # 2. Build ML dataset using Lag Features
    # Create lag features for close_price
    for i in range(1, actual_lags + 1):
        df[f'lag_{i}'] = df['close_price'].shift(i)
        
    df_clean = df.dropna().reset_index(drop=True)
    
    if len(df_clean) < 1:
        raise ValueError("Insufficient data after constructing lag features.")
    
    # Define features and target
    feature_cols = [f'lag_{i}' for i in range(1, actual_lags + 1)]
    X = df_clean[feature_cols].values
    y = df_clean['close_price'].values
    
    # 3. Train Linear Regression Model
    model = LinearRegression()
    model.fit(X, y)
    
    # Calculate R-squared
    if len(df_clean) > len(feature_cols) + 1:
        r2_score = float(model.score(X, y))
    else:
        r2_score = 1.0 # Perfect fit on small dataset
    logger.info(f"Model trained successfully. R^2 score: {r2_score:.4f}")
    
    # 4. Serialize and save the model to PostgreSQL
    import pickle
    model_bytes = pickle.dumps(model)
    model_name = f"linear-regression-lag-{actual_lags}"
    
    save_model_query = text("""
        INSERT INTO training.trained_models (symbol, model_name, model_data, r2_score)
        VALUES (:symbol, :model_name, :model_data, :r2_score)
        ON CONFLICT (symbol, model_name)
        DO UPDATE SET
            model_data = EXCLUDED.model_data,
            r2_score = EXCLUDED.r2_score,
            trained_at = NOW();
    """)
    
    with engine.begin() as conn:
        conn.execute(save_model_query, {
            "symbol": symbol,
            "model_name": model_name,
            "model_data": model_bytes,
            "r2_score": r2_score
        })
        
    logger.info(f"Saved trained model '{model_name}' for {symbol} to PostgreSQL.")
    
    return model, df_clean, r2_score, actual_lags
