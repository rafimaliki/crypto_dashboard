import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

app = FastAPI(title="ML Training Service", version="1.0.0")

class RetrainRequest(BaseModel):
    reason: str
    called_by: str

# MLflow config
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-service:5000")
EXPERIMENT_NAME = "BTC_Price_Prediction"
MODEL_NAME = "BTC_Predictor_Prod"

PARAMS = {
    "test_size": 0.2,
    "random_state": 42,
    "model_type": "LogisticRegression",
    "C_value": 1.0,
    "max_iter": 200,
    "max_target_gap_minutes": 10,
    "hold_threshold_percent": 0.1  # +/- 0.1% is considered HOLD
}

DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:5432/{os.getenv('DB_NAME')}"

def get_db_engine():
    return create_engine(DB_URL)

def load_and_process_data():
    engine = get_db_engine()
    
    print("Loading data from Postgres...")
    query = "SELECT * FROM btc_usd ORDER BY time ASC"
    df = pd.read_sql(query, engine)
    
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').reset_index(drop=True)
    df.set_index('time', inplace=True)
    
    df['SMA_12'] = df['close'].rolling(12).mean()
    df['volatility'] = df['high'] - df['low']
    
    df['next_close'] = df['close'].shift(-1)
    df['price_change_pct'] = ((df['next_close'] - df['close']) / df['close']) * 100
    
    hold_threshold = PARAMS["hold_threshold_percent"]
    df['target'] = 1
    df.loc[df['price_change_pct'] > hold_threshold, 'target'] = 2
    df.loc[df['price_change_pct'] < -hold_threshold, 'target'] = 0
    
    df['next_time'] = df.index.to_series().shift(-1)
    df['gap_minutes'] = (df['next_time'] - df.index).dt.total_seconds() / 60.0
    df['valid_target'] = df['gap_minutes'] <= PARAMS["max_target_gap_minutes"]
    
    df = df[df['valid_target']]
    
    df_final = df.dropna()
    
    features = ['close', 'volume', 'SMA_12', 'volatility']
    X = df_final[features]
    y = df_final['target']
    
    return X, y

def get_champion_accuracy(client, model_name):
    try:
        prod_models = client.get_latest_versions(model_name, stages=["Production"])
        
        if not prod_models:
            print("No 'Production' model found. Baseline accuracy is 0.0")
            return 0.0
            
        champion_version = prod_models[0]
        run_id = champion_version.run_id
        
        run_data = client.get_run(run_id).data
        champion_acc = run_data.metrics.get("accuracy", 0.0)
        
        print(f"Current Champion (v{champion_version.version}) Accuracy: {champion_acc:.4f}")
        return champion_acc
        
    except Exception as e:
        print(f"Error fetching champion: {e}. Assuming baseline 0.0")
        return 0.0

def execute_training(reason: str = None, called_by: str = None):
    print(f"Starting MLflow Training Job...")
    if reason:
        print(f"Reason: {reason}")
    if called_by:
        print(f"Called by: {called_by}")
    
    mlflow.end_run()
    
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    X, y = load_and_process_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=PARAMS["test_size"], random_state=PARAMS["random_state"]
    )
        
    with mlflow.start_run() as run:
        if reason:
            mlflow.set_tag("retrain_reason", reason)
        if called_by:
            mlflow.set_tag("called_by", called_by)
        print(f"Training {PARAMS['model_type']}...")
        
        mlflow.log_params(PARAMS)
        
        model = LogisticRegression(C=PARAMS["C_value"], max_iter=PARAMS["max_iter"])
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=PARAMS["C_value"], max_iter=PARAMS["max_iter"])
        )

        model.fit(X_train, y_train)
        
        predictions = model.predict(X_test)
        new_accuracy = accuracy_score(y_test, predictions)
        metrics = {
            "accuracy": new_accuracy,
            "precision_macro": precision_score(y_test, predictions, average='macro', zero_division=0),
            "recall_macro": recall_score(y_test, predictions, average='macro', zero_division=0),
            "precision_weighted": precision_score(y_test, predictions, average='weighted', zero_division=0),
            "recall_weighted": recall_score(y_test, predictions, average='weighted', zero_division=0)
        }
        mlflow.log_metrics(metrics)
        print(f"Metrics: {metrics}")
        
        input_example = X_train.head(1)
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            input_example=input_example,
            registered_model_name=MODEL_NAME
        )
        
        print("Model logged and registered to MLflow.")

        # save dataset
        dataset = mlflow.data.from_pandas(
            df=pd.concat([X_train, y_train], axis=1), 
            targets="target", 
            name="BTC_Candles_Train"
        )
        mlflow.log_input(dataset, context="training")

        # save dataset as csv
        train_dataset_path = "/tmp/train_dataset.csv"
        pd.concat([X_train, y_train], axis=1).to_csv(train_dataset_path, index=True)
        mlflow.log_artifact(train_dataset_path, artifact_path="data_snapshots")

        # client = MlflowClient()
        # champion_accuracy = get_champion_accuracy(client, MODEL_NAME)
        
        # promoted = False
        # if new_accuracy > champion_accuracy:
        #     print(f"Model promotion. Challenger ({new_accuracy:.4f}) beat Champion ({champion_accuracy:.4f})")
            
        #     latest_version_info = client.get_latest_versions(MODEL_NAME, stages=["None"])[0]
        #     new_version = latest_version_info.version
            
        #     client.transition_model_version_stage(
        #         name=MODEL_NAME,
        #         version=new_version,
        #         stage="Production",
        #         archive_existing_versions=True
        #     )
        #     print(f"Version {new_version} is now the Production model.")
        #     promoted = True
        # else:
        #     print(f"Model rejected. Challenger ({new_accuracy:.4f}) did not beat Champion ({champion_accuracy:.4f}).")

        client = MlflowClient()
        run_id = run.info.run_id

        model_name = "BTC_Predictor_Prod"
        versions = client.search_model_versions(f"name='{model_name}'")
        last_version = [v for v in versions if v.run_id == run_id][0]

        print(f"Promoting Version {last_version.version} to Production...")
        client.transition_model_version_stage(
            name=model_name,
            version=last_version.version,
            stage="Production",
            archive_existing_versions=True 
        )

        return {
            "run_id": run.info.run_id,
            "metrics": metrics,
            "champion_accuracy": new_accuracy,
            "promoted": True,
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/")
async def root():
    return {
        "service": "ML Training Service",
        "status": "healthy",
        "mlflow_uri": MLFLOW_URI,
        "model_name": MODEL_NAME
    }

@app.post("/retrain")
async def train_model(request: RetrainRequest, background_tasks: BackgroundTasks):
    try:
        result = execute_training(reason=request.reason, called_by=request.called_by)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Training completed successfully",
                "result": result
            }
        )
    except Exception as e:
        print(f"Training error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Training failed: {str(e)}"
            }
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)