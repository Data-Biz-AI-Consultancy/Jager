import datetime
import json
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sqlalchemy import Engine, text

logger = logging.getLogger("ml-service.predict")

def get_next_trading_day(current_date: datetime.date) -> datetime.date:
    """Helper to find the next trading day (skipping weekends)."""
    next_day = current_date + datetime.timedelta(days=1)
    # 5 is Saturday, 6 is Sunday
    while next_day.weekday() >= 5:
        next_day += datetime.timedelta(days=1)
    return next_day

def generate_predictions(
    engine: Engine,
    model: LinearRegression,
    df: pd.DataFrame,
    r2_score: float,
    actual_lags: int,
    symbol: str,
    prediction_days: int
):
    # Start with the most recent actual values from the dataset
    recent_lags = [float(df.iloc[-1]['close_price'])] + [float(df.iloc[-1][f'lag_{i}']) for i in range(1, actual_lags)]
    
    last_actual_price = float(df.iloc[-1]['close_price'])
    last_date = df.iloc[-1]['date']
    current_prediction_date = last_date
    
    predictions = []
    
    for day in range(1, prediction_days + 1):
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
            f"Step {day} of {prediction_days}-day autoregressive Linear Regression prediction. "
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
        
        # Save prediction to DB
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
                "symbol": symbol,
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
        
    logger.info(f"Generated {len(predictions)} step predictions for {symbol} starting on {predictions[0]['prediction_date']}")
    return predictions
