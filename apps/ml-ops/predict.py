import os
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import mlflow.pyfunc
from sqlalchemy import create_engine, text
from mlflow.tracking import MlflowClient

app = FastAPI()

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-service:5000")
MODEL_NAME = "BTC_Predictor_Prod"
STAGE = "Production"
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:5432/{os.getenv('DB_NAME')}"

model = None
model_version = None
model_identifier = None

def get_db_engine():
    return create_engine(DB_URL)

def get_latest_candle_features():
    engine = get_db_engine()
    
    query = """
        SELECT time, close, volume, high, low
        FROM btc_usd
        ORDER BY time DESC
        LIMIT 13
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        raise ValueError("No candle data available in database")
    
    df = df.sort_values('time').reset_index(drop=True)
    latest = df.iloc[-1]
    
    if len(df) >= 12:
        sma_12 = df['close'].iloc[-12:].mean()
    else:
        sma_12 = df['close'].mean()
    
    volatility = latest['high'] - latest['low']
    
    return {
        'close': float(latest['close']),
        'volume': float(latest['volume']),
        'SMA_12': float(sma_12),
        'volatility': float(volatility),
        'candle_time': latest['time'].isoformat() if hasattr(latest['time'], 'isoformat') else str(latest['time'])
    }

class MarketInput(BaseModel):
    close: float
    volume: float
    SMA_12: float
    volatility: float
    candle_time: Optional[str] = None

@app.on_event("startup")
def load_production_model():
    global model, model_version, model_identifier
    mlflow.set_tracking_uri(MLFLOW_URI)
    
    model_uri = f"models:/{MODEL_NAME}/{STAGE}"
    print(f"Connecting to MLflow at {MLFLOW_URI}...")
    print(f"Attempting to load model from: {model_uri}")
    
    try:
        model = mlflow.pyfunc.load_model(model_uri)
        
        client = MlflowClient()
        prod_models = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if prod_models:
            model_version = prod_models[0].version
            model_identifier = f"{MODEL_NAME}_v{model_version}"
            print(f"Production model loaded: {model_identifier}")
        else:
            model_identifier = f"{MODEL_NAME}_unknown"
            print("Production model loaded (version unknown)")
    except Exception as e:
        print(f"Failed to load model. Error: {e}")

@app.post("/predict")
def predict_next_move():
    load_production_model()
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded from MLflow")
    
    try:
        features = get_latest_candle_features()
        
        input_df = pd.DataFrame([{
            'close': features['close'],
            'volume': features['volume'],
            'SMA_12': features['SMA_12'],
            'volatility': features['volatility']
        }])
        
        prediction = model.predict(input_df)[0]
        label_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        label = label_map.get(int(prediction), "UNKNOWN")
        
        engine = get_db_engine()
        
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO prediction_logs 
                    (candle_time, model_identifier, predicted_label, close_price, volume, sma_12, volatility)
                    VALUES (:candle_time, :model_identifier, :predicted_label, :close_price, :volume, :sma_12, :volatility)
                """),
                {
                    "candle_time": features['candle_time'],
                    "model_identifier": model_identifier,
                    "predicted_label": int(prediction),
                    "close_price": features['close'],
                    "volume": features['volume'],
                    "sma_12": features['SMA_12'],
                    "volatility": features['volatility']
                }
            )
            conn.commit()
        
        return {
            "prediction": label,
            "prediction_value": int(prediction),
            "model_identifier": model_identifier,
            "candle_time": features['candle_time'],
            "input_features": features
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/update-prediction-logs")
def update_prediction_logs():
    try:
        engine = get_db_engine()
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    UPDATE prediction_logs pl
                    SET actual_label = CASE 
                        WHEN ((next_candle.close - current_candle.close) / current_candle.close * 100) > 0.1 THEN 2
                        WHEN ((next_candle.close - current_candle.close) / current_candle.close * 100) < -0.1 THEN 0
                        ELSE 1
                    END
                    FROM btc_usd current_candle
                    JOIN btc_usd next_candle ON next_candle.time > current_candle.time
                    WHERE pl.candle_time = current_candle.time
                      AND pl.actual_label IS NULL
                      AND next_candle.time = (
                          SELECT MIN(time) 
                          FROM btc_usd 
                          WHERE time > current_candle.time
                      )
                """)
            )
            conn.commit()
            updated_count = result.rowcount
        
        return {
            "status": "success",
            "updated_count": updated_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update error: {str(e)}")

@app.get("/metrics")
def get_model_metrics():
    try:
        engine = get_db_engine()
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        model_identifier,
                        COUNT(*) as total_predictions,
                        SUM(CASE WHEN actual_label IS NOT NULL THEN 1 ELSE 0 END) as labeled_predictions,
                        SUM(CASE WHEN predicted_label = actual_label THEN 1 ELSE 0 END) as correct_predictions,
                        ROUND(
                            100.0 * SUM(CASE WHEN predicted_label = actual_label THEN 1 ELSE 0 END) / 
                            NULLIF(SUM(CASE WHEN actual_label IS NOT NULL THEN 1 ELSE 0 END), 0),
                            2
                        ) as accuracy_percent
                    FROM prediction_logs
                    WHERE model_identifier = :model_identifier
                    GROUP BY model_identifier
                """),
                {"model_identifier": model_identifier}
            )
            row = result.fetchone()
        
        if not row:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "model_identifier": model_identifier,
                "total_predictions": 0,
                "labeled_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "status": "no_predictions"
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "model_identifier": row[0],
            "total_predictions": row[1],
            "labeled_predictions": row[2],
            "correct_predictions": row[3],
            "accuracy": float(row[4]) if row[4] else 0.0,
            "status": "active"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")
