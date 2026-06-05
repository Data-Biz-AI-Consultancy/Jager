import os
import datetime
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-service")

app = FastAPI(title="Jager Stock Prediction ML Service")

# DB Connection URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")
engine = create_engine(DATABASE_URL)

class PredictionRequest(BaseModel):
    symbol: str = "^GSPC"
    lag_days: int = 5

def get_next_trading_day(current_date: datetime.date) -> datetime.date:
    """Helper to find the next trading day (skipping weekends)."""
    next_day = current_date + datetime.timedelta(days=1)
    # 5 is Saturday, 6 is Sunday
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)
    return next_day

@app.post("/predict")
def predict_stock(req: PredictionRequest):
    logger.info(f"Received prediction request for symbol: {req.symbol}")
    
    # 1. Fetch historical data from DB
    query = text("""
        SELECT price_timestamp, close_price, open_price, volume
        FROM yahoo_finance_stock_prices
        WHERE symbol = :symbol
        ORDER BY price_timestamp ASC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"symbol": req.symbol})
        
    if df.empty or len(df) < (req.lag_days + 5):
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough historical price data for {req.symbol}. Required: at least {req.lag_days + 5} records."
        )
    
    # Preprocess
    df['price_timestamp'] = pd.to_datetime(df['price_timestamp'])
    df['date'] = df['price_timestamp'].dt.date
    # Drop duplicates by date, keeping the last one
    df = df.drop_duplicates(subset=['date'], keep='last').sort_values('date').reset_index(drop=True)
    
    # 2. Build ML dataset using Lag Features
    # Create lag features for close_price
    for i in range(1, req.lag_days + 1):
        df[f'lag_{i}'] = df['close_price'].shift(i)
        
    df = df.dropna().reset_index(drop=True)
    
    if len(df) < 5:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient data after constructing lag features."
        )
    
    # Define features and target
    feature_cols = [f'lag_{i}' for i in range(1, req.lag_days + 1)]
    X = df[feature_cols].values
    y = df['close_price'].values
    
    # 3. Train Linear Regression Model
    model = LinearRegression()
    model.fit(X, y)
    
    # Calculate R-squared for logging / metadata
    r2_score = float(model.score(X, y))
    logger.info(f"Model trained successfully. R^2 score: {r2_score:.4f}")
    
    # 4. Predict the next day's price
    # The feature vector for the next prediction is the most recent close prices
    most_recent_data = df.iloc[-1]
    last_actual_price = float(most_recent_data['close_price'])
    last_date = most_recent_data['date']
    
    # Feature vector for next day prediction: [close(t), close(t-1), close(t-2), ...]
    # Which corresponds to [lag_0, lag_1, lag_2, ...] relative to tomorrow
    next_features = [last_actual_price] + [float(most_recent_data[f'lag_{i}']) for i in range(1, req.lag_days)]
    next_features_arr = np.array(next_features).reshape(1, -1)
    
    predicted_price = float(model.predict(next_features_arr)[0])
    
    # Determine predicted trend
    if predicted_price > last_actual_price:
        trend = "UP"
    elif predicted_price < last_actual_price:
        trend = "DOWN"
    else:
        trend = "FLAT"
        
    prediction_date = get_next_trading_day(last_date)
    
    # Simple heuristic confidence score based on R-squared (bounded [0, 1])
    confidence = max(0.0, min(1.0, r2_score))
    
    reasoning = (
        f"Linear Regression trained on {len(df)} days of historical data. "
        f"R-squared: {r2_score:.4f}. Lag inputs: {[round(x, 2) for x in next_features]}."
    )
    
    features_json = {
        "lags": next_features,
        "r2": r2_score,
        "last_actual_price": last_actual_price,
        "last_date": str(last_date)
    }
    
    model_name = f"linear-regression-lag-{req.lag_days}"
    
    # 5. Save prediction to DB
    insert_query = text("""
        INSERT INTO prediction.stock_predictions 
        (symbol, prediction_date, predicted_close_price, trend, confidence, reasoning, model_name, features)
        VALUES (:symbol, :prediction_date, :predicted_close_price, :trend, :confidence, :reasoning, :model_name, :features)
        ON CONFLICT (symbol, prediction_date, model_name)
        DO UPDATE SET
            predicted_close_price = EXCLUDED.predicted_close_price,
            trend = EXCLUDED.trend,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            features = EXCLUDED.features,
            created_at = NOW();
    """)
    
    import json
    with engine.begin() as conn:
        conn.execute(insert_query, {
            "symbol": req.symbol,
            "prediction_date": prediction_date,
            "predicted_close_price": predicted_price,
            "trend": trend,
            "confidence": confidence,
            "reasoning": reasoning,
            "model_name": model_name,
            "features": json.dumps(features_json)
        })
        
    logger.info(f"Saved prediction for {req.symbol} on {prediction_date}: {predicted_price:.2f} ({trend})")
    
    return {
        "status": "success",
        "symbol": req.symbol,
        "prediction_date": str(prediction_date),
        "predicted_close_price": predicted_price,
        "trend": trend,
        "confidence": confidence,
        "reasoning": reasoning,
        "model_name": model_name
    }

@app.post("/evaluate")
def evaluate_predictions():
    logger.info("Starting prediction evaluation...")
    
    # Find all predictions with missing actual close price
    find_query = text("""
        SELECT id, symbol, prediction_date
        FROM prediction.stock_predictions
        WHERE actual_close_price IS NULL
    """)
    
    update_count = 0
    
    with engine.connect() as conn:
        predictions = conn.execute(find_query).fetchall()
        
    for pred in predictions:
        pred_id, symbol, pred_date = pred
        
        # Check if we have an actual close price for this date
        check_query = text("""
            SELECT close_price
            FROM yahoo_finance_stock_prices
            WHERE symbol = :symbol AND price_timestamp::date = :pred_date
            ORDER BY price_timestamp DESC
            LIMIT 1
        """)
        
        with engine.connect() as conn:
            actual = conn.execute(check_query, {"symbol": symbol, "pred_date": pred_date}).fetchone()
            
        if actual:
            actual_price = float(actual[0])
            # Update the prediction record
            update_query = text("""
                UPDATE prediction.stock_predictions
                SET actual_close_price = :actual_close_price
                WHERE id = :id
            """)
            with engine.begin() as conn:
                conn.execute(update_query, {"actual_close_price": actual_price, "id": pred_id})
            logger.info(f"Updated prediction ID {pred_id} ({symbol} for {pred_date}) with actual price {actual_price:.2f}")
            update_count += 1
            
    return {
        "status": "success",
        "evaluated_records_count": update_count
    }
