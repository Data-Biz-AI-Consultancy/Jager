import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from train import train_model
from predict import generate_predictions
from backtest import run_backtest

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

class BacktestRequest(BaseModel):
    symbol: str = "^GSPC"
    lag_days: int = 5
    exclude_last_days: int = 14
    predict_days: int = 7

@app.post("/predict")
def predict_stock(req: PredictionRequest):
    logger.info(f"Received prediction request for symbol: {req.symbol}, forecasting {req.prediction_days} days")
    
    try:
        # 1. Train model
        model, df, r2_score, actual_lags = train_model(engine, req.symbol, req.lag_days)
        
        # 2. Generate predictions
        predictions = generate_predictions(
            engine=engine,
            model=model,
            df=df,
            r2_score=r2_score,
            actual_lags=actual_lags,
            symbol=req.symbol,
            prediction_days=req.prediction_days
        )
        
        return {
            "status": "success",
            "symbol": req.symbol,
            "predictions": predictions,
            "model_name": f"linear-regression-lag-{actual_lags}"
        }
        
    except ValueError as e:
        logger.error(f"Value error during prediction execution: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during prediction execution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred.")

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
            FROM s_yahoo_finance.stock_prices
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

@app.post("/backtest")
def backtest_model(req: BacktestRequest):
    logger.info(f"Received backtest request for symbol: {req.symbol}, excluding last {req.exclude_last_days} days to predict {req.predict_days} days")
    try:
        res = run_backtest(
            engine=engine,
            symbol=req.symbol,
            lag_days=req.lag_days,
            exclude_last_days=req.exclude_last_days,
            predict_days=req.predict_days
        )
        return res
    except ValueError as e:
        logger.error(f"Value error during backtest execution: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during backtest execution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred.")
