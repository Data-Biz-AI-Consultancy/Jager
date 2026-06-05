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
    prediction_days: int = 7

def get_next_trading_day(current_date: datetime.date) -> datetime.date:
    """Helper to find the next trading day (skipping weekends)."""
    next_day = current_date + datetime.timedelta(days=1)
    # 5 is Saturday, 6 is Sunday
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)
    return next_day

@app.post("/predict")
def predict_stock(req: PredictionRequest):
    logger.info(f"Received prediction request for symbol: {req.symbol}, forecasting {req.prediction_days} days")
    
    # 1. Fetch historical data from DB
    query = text("""
        SELECT price_timestamp, close_price, open_price, volume
        FROM yahoo_finance_stock_prices
        WHERE symbol = :symbol
        ORDER BY price_timestamp ASC
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"symbol": req.symbol})
        
    if df.empty or len(df) < 2:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough historical price data for {req.symbol}. Required: at least 2 records."
        )
    
    # Preprocess
    df['price_timestamp'] = pd.to_datetime(df['price_timestamp'])
    df['date'] = df['price_timestamp'].dt.date
    # Drop duplicates by date, keeping the last one
    df = df.drop_duplicates(subset=['date'], keep='last').sort_values('date').reset_index(drop=True)
    
    # Dynamic adjustment of lag_days based on available unique dates
    actual_lags = req.lag_days
    if len(df) <= actual_lags:
        actual_lags = max(1, len(df) - 2)
        logger.warning(f"Insufficient data for requested lag_days={req.lag_days}. Dynamically reducing to {actual_lags}")
        
    # 2. Build ML dataset using Lag Features
    # Create lag features for close_price
    for i in range(1, actual_lags + 1):
        df[f'lag_{i}'] = df['close_price'].shift(i)
        
    df = df.dropna().reset_index(drop=True)
    
    if len(df) < 1:
        raise HTTPException(
            status_code=400, 
            detail="Insufficient data after constructing lag features."
        )
    
    # Define features and target
    feature_cols = [f'lag_{i}' for i in range(1, actual_lags + 1)]
    X = df[feature_cols].values
    y = df['close_price'].values
    
    # 3. Train Linear Regression Model
    model = LinearRegression()
    model.fit(X, y)
    
    # Calculate R-squared for logging / metadata
    if len(df) > len(feature_cols) + 1:
        r2_score = float(model.score(X, y))
    else:
        r2_score = 1.0 # Perfect fit on small dataset
    logger.info(f"Model trained successfully. R^2 score: {r2_score:.4f}")
    
    # 4. Predict the next N days iteratively (autoregressive)
    # Start with the most recent actual values from the dataset
    recent_lags = [float(df.iloc[-1]['close_price'])] + [float(df.iloc[-1][f'lag_{i}']) for i in range(1, actual_lags)]
    
    last_actual_price = float(df.iloc[-1]['close_price'])
    last_date = df.iloc[-1]['date']
    current_prediction_date = last_date
    
    predictions = []
    
    import json
    for day in range(1, req.prediction_days + 1):
        # Feature vector for the next step prediction
        features_arr = np.array(recent_lags[:actual_lags]).reshape(1, -1)
        predicted_price = float(model.predict(features_arr)[0])
        
        # Determine predicted trend relative to last actual price
        if predicted_price > last_actual_price:
            trend = "UP"
        elif predicted_price < last_actual_price:
            trend = "DOWN"
        else:
            trend = "FLAT"
            
        current_prediction_date = get_next_trading_day(current_prediction_date)
        confidence = max(0.0, min(1.0, r2_score))
        
        reasoning = (
            f"Step {day} of {req.prediction_days}-day autoregressive Linear Regression prediction. "
            f"Lag inputs: {[round(x, 2) for x in recent_lags[:actual_lags]]}."
        )
        
        features_json = {
            "lags": recent_lags[:actual_lags],
            "r2": r2_score,
            "step": day,
            "last_actual_price": last_actual_price,
            "last_date": str(last_date)
        }
        
        model_name = f"linear-regression-lag-{actual_lags}"
        
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
        
        with engine.begin() as conn:
            conn.execute(insert_query, {
                "symbol": req.symbol,
                "prediction_date": current_prediction_date,
                "predicted_close_price": predicted_price,
                "trend": trend,
                "confidence": confidence,
                "reasoning": reasoning,
                "model_name": model_name,
                "features": json.dumps(features_json)
            })
            
        predictions.append({
            "step": day,
            "prediction_date": str(current_prediction_date),
            "predicted_close_price": predicted_price,
            "trend": trend,
            "reasoning": reasoning
        })
        
        # Autoregressive update: insert new prediction at the start of lags list, and drop the oldest
        recent_lags = [predicted_price] + recent_lags[:-1]
        
    logger.info(f"Generated {len(predictions)} step predictions for {req.symbol} starting on {predictions[0]['prediction_date']}")
    
    return {
        "status": "success",
        "symbol": req.symbol,
        "predictions": predictions,
        "model_name": f"linear-regression-lag-{actual_lags}"
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
